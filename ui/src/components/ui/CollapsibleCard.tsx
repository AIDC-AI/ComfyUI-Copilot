import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface IProps {
  title?: string | React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

const CollapsibleCard: React.FC<IProps> = (props) => {
  const { title = '', className = '', children } = props;
  
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div className={`border border-gray-200 dark:border-gray-600 rounded-lg p-4 ${className}`}>
      <div className="flex justify-between items-center mb-4">
        <div>
        {
          typeof title === 'string' ? <h3 className="text-sm text-gray-900 dark:text-white font-medium mb-4">{title}</h3> : title
        }
        </div>
        <button
          onClick={() => setIsOpen(!isOpen)}
        >
          {
            isOpen ? <ChevronUp /> : <ChevronDown />
          }
        </button>
      </div>
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
      {
        isOpen && children
      }
      </div>
    </div>
  )
}

export default CollapsibleCard;