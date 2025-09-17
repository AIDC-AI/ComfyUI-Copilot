import { ReactNode, useState } from "react";
import { Portal } from "../chat/Portal";

interface IProps {
  buttonClass: string
  buttonContent: ReactNode | string
  renderModal: (onClose: () => void) => ReactNode
  onOpen?: () => void
}

const ButtonWithModal: React.FC<IProps> = (props) => {
  const { buttonClass = '', buttonContent, renderModal, onOpen } = props

  const [open, setOpen] = useState<boolean>(false)

  return <>
    <button
      className={buttonClass}
      onClick={() => {
        onOpen && onOpen()
        setOpen(true)
      }}
    >
      {buttonContent}
    </button>
    {
      open && <Portal>
        {
          renderModal && renderModal(() => setOpen(false))
        }
      </Portal>
    }
  </>
}

export default ButtonWithModal;