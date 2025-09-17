import { useEffect, useState } from "react";
import { app } from "../../../utils/comfyapp";
import Modal from "../../ui/Modal";
import { useChatContext } from "../../../context/ChatContext";
import LoadingIcon from "../../ui/LoadingIcon";
import { Select, Table, type TableProps } from 'antd';
import TableEmpty from "../../ui/TableEmpty";
import { WorkflowChatAPI } from "../../../apis/workflowChatApi";
import Tag from "../../ui/Tag";
interface IProps {
  modelList: any[]
  loading?: boolean
  showTitle?: boolean
  showPagination?: boolean
}

type ColumnsType<T extends object> = TableProps<T>['columns'];

type DataType = {
  Id: number
  Name: string
  Path: string
  ChineseName?: string
  LastUpdatedTime?: number
  Downloads?: number
  Libraries?: string[]
  source_model_type?: string
  source_missing_model?: string
  source_keyword?: string
  model_type?: string
}

const TITLE_ZH = '发现模型缺失，推荐下载以下模型。'
const TITLE_EN = 'Missing models detected. We recommend downloading the following models.'

const TH_ZH = {
  name: '模型ID',
  dir: '模型下载存放目录',
  tags: '标签',
  updateTime: '更新时间',
  downloads: '下载量',
  action: '操作'
}

const TH_EN = {
  name: 'Model ID',
  dir: 'Models download directory',
  tags: 'Tags',
  updateTime: 'Update time',
  downloads: 'Downloads',
  action: 'Action'
}

const ModelOption: React.FC<IProps> = (props) => {
  const { modelList, loading = false, showTitle = true, showPagination = true } = props
  const { modelDownloadMap, addDownloadId } = useChatContext()

  const browserLanguage = app.extensionManager.setting.get('Comfy.Locale');
  const [modelPaths, setModelPaths] = useState<string[] | null>(null)
  const [selectedPathMap, setSelectedPathMap] = useState<Record<number, string>>({})
  const [modalContent, setModalContent] = useState<string | null>(null)
  const thMap = browserLanguage === 'zh' ? TH_ZH : TH_EN

  const getModelPaths = async () => {
    const response = await fetch('/api/model-paths')
    const res = await response.json()
    setModelPaths(res?.data?.paths || [])
  }

  useEffect(() => {
    getModelPaths()
  }, [])
  
  useEffect(() => {
    if (!modelPaths || modelPaths.length === 0) 
      return
    let selectedPaths: Record<number, string> = {}
    modelList?.forEach(item => { 
      const index = modelPaths.findIndex((path: string) => item.model_type === path)
      selectedPaths[item.Id] = modelPaths[index === -1 ? 0 : index] || ''
    })
    setSelectedPathMap(selectedPaths)
  }, [modelList, modelPaths])

  const handleDownload = async (id: number, modelId: string, modelType: string) => {
    WorkflowChatAPI.trackEvent({
      event_type: 'model_download_trigger',
      message_type: 'model',
      data: { id, model_id: modelId, model_type: modelType || selectedPathMap[id] }
    })
    let body: Record<string, string | number> = {
      id,
      model_id: modelId,
      model_type: !!modelType && modelType !== '' ? modelType : selectedPathMap[id],
    }
    // if (!!selectedPathMap[id] && selectedPathMap[id] !== '') {
    //   body['dest_dir'] = selectedPathMap[id]
    // }
    const response = await fetch('/api/download-model', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    const res = await response.json()
    if (!res.success) {
      setModalContent(res.message || 'Download Model Failed!')
    } else {
      addDownloadId(res.data.download_id)
    }
  }

  const handleSelectedPath = (id: number, path: string) => {
    setSelectedPathMap(prev => ({
      ...prev,
      [id]: path
    }))
  }

  const renderDownloadProgress = (status: string) => {
    if (status === 'completed') {
      return <svg className="w-5 h-5" viewBox="0 0 1024 1024" fill="#13d320">
        <path d="M198.920606 353.438906l294.89452 398.030819-141.866143 105.106304-294.89452-398.030819 141.866143-105.106304Z">
        </path>
        <path d="M292.668567 679.383279l612.100893-449.37515 104.488343 142.3252-612.100893 449.37515-104.488343-142.3252Z">
        </path>
      </svg>
    } else if (status === 'downloading') {
      return <LoadingIcon className="w-5 h-5 text-gray-700"/>
    } else {
      return null
    }
  }

  const columns: ColumnsType<DataType> = [
    {
      title: thMap.name,
      key: 'modelId',
      render: (_, record) => (
        <div>{`${record.Path}/${record.Name}`}</div>
      )
    },
    {
      title: thMap.dir,
      key: 'directory',
      render: (_, record) => (
        // <select
        //   value={selectedPathMap[record.Id]}
        //   onChange={(e) => handleSelectedPath(record.Id, e.target.value)}
        //   className="px-1.5 py-0.5 text-xs rounded-md bg-gray-100
        //           text-gray-700 focus:outline-none focus:ring-2 
        //           focus:ring-blue-500 hover:!bg-gray-50"
        // >
        //   {modelPaths?.map((path: string) => (
        //       <option value={path} key={path}>{path}</option>
        //   ))}
        // </select>
        <Select 
          value={selectedPathMap[record.Id]}
          onChange={(value) => handleSelectedPath(record.Id, value)}
          options={modelPaths?.map((path: string) => ({
            label: path,
            value: path
          }))}
          className="w-full"
          suffixIcon={<div className="text-gray-600">
            <svg viewBox="0 0 1024 1024" className="w-5 h-5" fill="currentColor">
              <path d="M512 714.666667c-8.533333 0-17.066667-2.133333-23.466667-8.533334l-341.333333-341.333333c-12.8-12.8-12.8-32 0-44.8 12.8-12.8 32-12.8 44.8 0l320 317.866667 317.866667-320c12.8-12.8 32-12.8 44.8 0 12.8 12.8 12.8 32 0 44.8L533.333333 704c-4.266667 8.533333-12.8 10.666667-21.333333 10.666667z">
              </path>
            </svg>
          </div>}
        />
      )
    },
    {
      title: thMap.tags,
      key: 'tags',
      render: (_, record) => (
        <div className="flex flex-wrap gap-1">{record?.Libraries?.map((item: string) => <Tag content={item} />)}</div>
      )
    },
    {
      title: thMap.updateTime,
      key: 'updateTime',
      render: (_, record) => (
        <div>{record.LastUpdatedTime ? new Date(record.LastUpdatedTime).toLocaleString() : ''}</div>
      )
    },
    {
      title: thMap.downloads,
      key: 'downloads',
      render: (_, record) => (
        <div>{record.Downloads ? record.Downloads : 0}</div>
      )
    },
    {
      title: thMap.action,
      key: 'action',
      render: (_, record) => (
        <div className="w-full h-full flex justify-center items-center">
          {
            (!!modelDownloadMap[record.Id] && modelDownloadMap[record.Id].status !== 'failed') ? renderDownloadProgress(modelDownloadMap[record.Id]?.status) : <button 
              className="text-gray-900 hover:!text-blue-500 disabled:!text-gray-300 flex justify-center items-center bg-transparent border-none"
              disabled={!!modelDownloadMap[record.Id]}
              onClick={() => handleDownload(record.Id, `${record.Path}/${record.Name}`, record?.model_type || '')}
            >
              <svg viewBox="0 0 1071 1024" className="w-5 h-5" fill="currentColor">
                <path d="M1022.955204 522.570753c0 100.19191-81.516572 181.698249-181.718715 181.698249l-185.637977 0c-11.2973 0-20.466124-9.168824-20.466124-20.466124 0-11.307533 9.168824-20.466124 20.466124-20.466124l185.637977 0c77.628008 0 140.786467-63.148226 140.786467-140.766001 0-77.423347-62.841234-140.448776-140.203182-140.766001-0.419556 0.030699-0.818645 0.051165-1.217734 0.061398-5.945409 0.143263-11.686157-2.292206-15.687284-6.702656-4.001127-4.400217-5.894244-10.335393-5.167696-16.250102 1.330298-10.806113 1.944282-19.760043 1.944282-28.192086 0-60.763922-23.658839-117.884874-66.617234-160.833035-42.968627-42.968627-100.089579-66.617234-160.843268-66.617234-47.368844 0-92.742241 14.449084-131.208321 41.781592-37.616736 26.738991-65.952084 63.700811-81.925894 106.884332-2.425236 6.538927-8.012488 11.399631-14.827707 12.893658-6.815219 1.483794-13.927197-0.603751-18.859533-5.54632-19.289322-19.330254-44.943608-29.972639-72.245418-29.972639-56.322773 0-102.146425 45.813419-102.146425 102.125959 0 0.317225 0.040932 0.982374 0.092098 1.627057 0.061398 0.920976 0.122797 1.831718 0.153496 2.762927 0.337691 9.465582-5.863545 17.928325-15.001669 20.455891-32.356942 8.933463-61.541635 28.550243-82.181721 55.217602-21.305235 27.516704-32.571836 60.508096-32.571836 95.41307 0 86.244246 70.188572 156.422585 156.443052 156.422585l169.981393 0c11.2973 0 20.466124 9.15859 20.466124 20.466124 0 11.2973-9.168824 20.466124-20.466124 20.466124l-169.981393 0c-108.828614 0-197.3753-88.536452-197.3753-197.354833 0-44.053332 14.223956-85.712127 41.126676-120.473839 22.809495-29.460985 53.897537-52.086285 88.710414-64.816215 5.065366-74.322729 67.149353-133.2447 142.751215-133.2447 28.386514 0 55.504128 8.217149 78.651314 23.52581 19.657712-39.868009 48.842405-74.169233 85.497233-100.212376 45.434795-32.295544 99.004875-49.354058 154.918325-49.354058 71.692832 0 139.087778 27.915793 189.782368 78.600149 50.694589 50.694589 78.610382 118.089535 78.610382 189.782368 0 3.704368-0.102331 7.470135-0.296759 11.368932C952.633602 352.568894 1022.955204 429.511287 1022.955204 522.570753z" p-id="4439">
                </path>
                <path d="M629.258611 820.711014l-102.023628 102.013395c-3.990894 4.001127-9.230222 5.996574-14.46955 5.996574s-10.478655-1.995447-14.46955-5.996574l-102.023628-102.013395c-7.992021-7.992021-7.992021-20.947078 0-28.939099s20.947078-8.002254 28.939099 0l67.087954 67.077721 0-358.699522c0-11.2973 9.15859-20.466124 20.466124-20.466124 11.307533 0 20.466124 9.168824 20.466124 20.466124l0 358.699522 67.087954-67.077721c7.992021-8.002254 20.947078-7.992021 28.939099 0S637.250632 812.718993 629.258611 820.711014z" p-id="4440">
                </path>
              </svg>
            </button>
          }
        </div>
      ),
      fixed: 'right'
    },
  ];

  if (!modelPaths) 
    return null

  return <div className="mt-4 w-full h-auto flex-1 min-h-0 overflow-y-auto">
    {
      showTitle && <h3 className="text-xl text-gray-900 font-bold">
        {browserLanguage === 'zh' ? TITLE_ZH : TITLE_EN}
      </h3>
    }
    <Table  
      id="comfyui-copilot-model-download"
      // bordered
      loading={loading}
      columns={columns} 
      dataSource={modelList} 
      pagination={showPagination ? undefined : false}
      rowClassName={"text-gray-800"}
      locale={{ emptyText: <TableEmpty /> }}
    />
    <Modal open={!!modalContent && modalContent !== ''} onClose={() => setModalContent(null)}>
      <p>{modalContent}</p>
    </Modal>
  </div>
}

export default ModelOption