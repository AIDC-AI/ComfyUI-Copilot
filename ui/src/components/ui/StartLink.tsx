import { github_url } from "../../config";

interface IProps {
    children: React.ReactNode;
    className?: string
}

const StartLink = ({ children, className = '' }: IProps) => {
    return (
        <a 
          className={`text-xs text-gray-600 font-normal text-center ${className}`}
          href={github_url}
          target="_blank" 
          rel="noopener noreferrer">
            {children}
        </a>
    )
}

export default StartLink;