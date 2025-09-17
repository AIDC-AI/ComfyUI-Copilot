import { useEffect, useRef, useState } from "react";
import { createRewriteExpert, deleteRewriteExpert, getRewriteExpertsList, updateRewriteExpert } from "../../apis/rewriteExpertApi";
import { Button, Form, Space, Table, type TableProps } from 'antd';
import { Input } from 'antd';
import { XIcon, TrashIcon, CirclePlusIcon, FilePenLineIcon } from "./Icons";
import { debounce } from "lodash";
import Modal from '../ui/Modal';
import TableEmpty from "../ui/TableEmpty";

const { TextArea } = Input

interface IProps {
  onClose: () => void
}

type ColumnsType<T extends object> = TableProps<T>['columns'];

type DataType = {
  id: number
  name: string
  description: string
  content: string
}

const RewriteExpertModal: React.FC<IProps> = ({onClose}) => {  
  const [dataList, setDataList] = useState<DataType[]>([])
  const [searchValue, setSearchValue] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [currentDataList, setCurrentDataList] = useState<DataType[]>([])
  const [modalContent, setModalContent] = useState<string | null>(null)
  const [editData, setEditData] = useState<DataType | null>(null)
  const isAdd = useRef<boolean>(false)
  
  const onEdit = (item: DataType) => {
    setEditData(item)
  }

  const onDelete = async (id: number) => {
    if (id < 1) return
    try {
      const res = await deleteRewriteExpert(id)
      if (!!res.success) {
        setModalContent('Delete success')
        queryGetRewriteExpertsList()
      }
    } catch (error) {
      console.log('error---_>', error)
      setModalContent(`Delete error: ${error}`)
    }
  }

  const queryGetRewriteExpertsList = async () => {
    setLoading(true)
    try {
      const res = await getRewriteExpertsList()
      if (!!res.success && !!res?.data?.experts) {
        setDataList(res.data.experts)
        setCurrentDataList(res.data.experts)
      }
    } catch (error) {
      setModalContent(`Get list error: ${error}`)
      console.log('error---_>', error)
    } finally {
      setLoading(false)
    }
  }  

  const handleSetCurrentDataList = (value: string) => {
    if (value === '') {
      setCurrentDataList(dataList)
    } else {
      setCurrentDataList(dataList.filter(item => item.name.includes(value)))
    }
  }

  const handleAddRewriteExpert = () => {
    isAdd.current = true
    setEditData({
      id: 0,
      name: '',
      description: '',
      content: ''
    })
  }

  const handleSearchRewriteExpert = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const value = e.target.value
    handleSetCurrentDataList(value)
    setSearchValue(value)
  }

  const onFinish = async (values: any) => {
    let func = null
    if (isAdd.current) {
      func = createRewriteExpert
    } else {
      func = updateRewriteExpert
    }
    try {
      const res = await func(values)
      if (!!res.success) {
        setModalContent(isAdd.current ? 'Add success' : 'Edit success')
        queryGetRewriteExpertsList()
        setEditData(null)
      }
    } catch (error) {
      setModalContent(isAdd.current ? `Add error ${error}` : `Edit error ${error}`)
    }
  }

  const onCancel = () => {
    setEditData(null)
    isAdd.current = false
  }

  useEffect(() => {
    queryGetRewriteExpertsList()
  }, [])

  const columns: ColumnsType<DataType> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      ellipsis: { showTitle: true }
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: { showTitle: true }
    },
    {
      title: 'Content',
      dataIndex: 'content',
      key: 'content',
      ellipsis: { showTitle: true }
    },
    {
      title: 'Action',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <button 
            onClick={() => onEdit(record)}
            className="bg-transparent border-none text-gray-500 hover:!text-gray-700"
          >
            <FilePenLineIcon className="w-5 h-5" />
          </button>
          <button 
            onClick={() => onDelete(record.id)}
            className="bg-transparent border-none text-gray-500 hover:!text-gray-700"
          >
            <TrashIcon className="w-5 h-5" />
          </button>
        </Space>
      )
    },
  ];

  return (
    <div 
      id='comfyui-copilot-rewrite-expert-modal' 
      className="fixed inset-0 bg-[rgba(0,0,0,0.5)] flex items-center justify-center"
      style={{
        backgroundColor: 'rgba(0,0,0,0.5)'
      }}
    >
      <div className="relative bg-white rounded-xl p-6 w-1/2 h-2/3 flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl text-gray-900 dark:text-white font-semibold">Set expert experience to help you rewrite workflow</h2>
          <button 
            onClick={onClose}
            disabled={loading}
            className="bg-white border-none text-gray-500 hover:!text-gray-700"
          >
            <XIcon className="w-5 h-5" />
          </button>
        </div>
        <div className="flex justify-between mb-2">
          <Input 
            placeholder="Enter search name" 
            allowClear
            value={searchValue}
            disabled={loading}
            onChange={debounce(handleSearchRewriteExpert, 500)}
            className="search-input w-1/4 bg-white text-[#888] placeholder-gray-500 border border-gray-300"
          />
          <button
            onClick={handleAddRewriteExpert}
            className="bg-white border-none text-gray-500 hover:!text-gray-700"
          >
            <CirclePlusIcon className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto">
          <Table 
            bordered
            loading={loading}
            columns={columns} 
            dataSource={currentDataList} 
            rowClassName={"text-gray-800"}
            locale={{ emptyText: <TableEmpty /> }}
          />
        </div>
        {
          editData && <div className="absolute top-0 left-0 w-full h-full bg-white rounded-xl p-6 z-5 overflow-y-auto">
            <h2 className="text-xl text-gray-900 dark:text-white font-semibold">{`${editData?.name && editData?.name !== '' ? 'Edit' : 'Add'} Rewrite Expert`}</h2>
            <Form
              onFinish={onFinish}
              initialValues={editData}
              layout="vertical"
            >
              <Form.Item
                name="id" 
                label="Id" 
                hidden
              >
                <Input 
                  disabled 
                />
              </Form.Item>
              <Form.Item 
                name="name" 
                label="Name" 
                rules={[{ required: true }]}
              >
                <Input 
                  placeholder="Enter name" 
                />
              </Form.Item>
              <Form.Item 
                name="description" 
                label="Description" 
                rules={[{ required: true }]}
              >
                <TextArea 
                  placeholder="Enter description" 
                  autoSize={{ maxRows: 6 }}
                />
              </Form.Item>
              <Form.Item 
                name="content" 
                label="Content" 
                rules={[{ required: true }]}
              >
                <TextArea 
                  placeholder="Enter content" 
                  autoSize={{ maxRows: 10 }}
                />
              </Form.Item>
              <Form.Item>
                <Space align='end' size='middle'>
                  <Button type="primary" htmlType="submit">
                    Submit
                  </Button>
                  <Button onClick={onCancel}>
                    Cancel
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </div>
        }
      </div>
      <Modal open={!!modalContent && modalContent !== ''} onClose={() => setModalContent(null)}>
        <p>{modalContent}</p>
      </Modal>
    </div>
  );
}

export default RewriteExpertModal;