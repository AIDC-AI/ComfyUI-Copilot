import { XIcon } from "../chat/Icons"

interface IProps {
  onClose?: () => void
  loading?: boolean
}

const ButtonClose: React.FC<IProps> = ({ onClose = () => {}, loading = false }) => {
  return (
    <button 
      onClick={onClose}
      disabled={loading}
      className="bg-white border-none text-gray-500 hover:!text-gray-700"
    >
      <XIcon className="w-5 h-5" />
    </button>
  )
}

export default ButtonClose