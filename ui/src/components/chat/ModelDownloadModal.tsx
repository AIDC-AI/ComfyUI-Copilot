import { useEffect, useRef, useState } from "react";
import { XIcon } from "./Icons";
import { Input } from 'antd';
import { debounce } from "lodash";
import ModelOption from "./messages/ModelOption";
import type { InputRef } from 'antd';

interface IProps {
  onClose: () => void
}

const ModelDownloadModal: React.FC<IProps> = (props) => {
  const { onClose } = props;

  const [loading, setLoading] = useState<boolean>(false)
  const [modelSuggests, setModelSuggests] = useState<any[]>([])
  const ref = useRef<InputRef>(null)

  useEffect(() => {
    ref?.current?.focus()
  }, [modelSuggests])

  const getModelSuggests = async (keyword: string) => {
    setLoading(true)
    try {
      const response = await fetch(`/api/model-suggests?keyword=${keyword}`)
      const data = await response.json()
      setModelSuggests(data?.data?.suggests || [])
    } catch (e) {
      console.log('e--->',e)
    } finally {
      setLoading(false)
    }
  }

  const handleSearchModel = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    getModelSuggests(e.target.value)
  }

  return <div 
    id="comfyui-copilot-model-download-modal" 
    className="fixed inset-0 bg-[rgba(0,0,0,0.5)] flex items-center justify-center"
    style={{
        backgroundColor: 'rgba(0,0,0,0.5)'
    }}
  >
    <div className="relative bg-white rounded-xl p-6 w-1/2 h-1/2 flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl text-gray-900 font-semibold">Model Download</h2>
        <button 
          onClick={onClose}
          disabled={loading}
          className="bg-white border-none text-gray-500 hover:!text-gray-700"
        >
          <XIcon className="w-5 h-5" />
        </button>
      </div>
      <div className="flex justify-start mb-2">
        <Input 
          ref={ref}
          placeholder="Enter search name" 
          allowClear
          disabled={loading}
          onChange={debounce(handleSearchModel, 500)}
          className="search-input w-1/4 bg-white text-[#888] placeholder-gray-500 border border-gray-300"
        />
      </div>
      <ModelOption modelSuggests={modelSuggests} loading={loading} showTitle={false} />
    </div>
  </div>
}

export default ModelDownloadModal;