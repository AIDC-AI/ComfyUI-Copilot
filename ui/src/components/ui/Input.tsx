import { useState } from "react";
import { debounce } from "lodash";

interface IProps {
  isPassword?: boolean;
  value?: string;
  setValue?: (value: string) => void;
  setIsValueValid?: (value: string) => void;
  placeholder?: string;
  className?: string;
}

const Input: React.FC<IProps> = (props) => {
  const { isPassword = false, value = '', setValue = () => {}, setIsValueValid, placeholder = '', className = '' } = props;
  const [showPassword, setShowPassword] = useState(!isPassword);
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
    setIsValueValid?.(e.target.value);
  }

  return (
    <div className={`relative ${className}`}>
      <input
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          className="w-full px-4 py-3 border border-gray-200 dark:border-gray-600 rounded-lg
          bg-gray-50 dark:bg-gray-700 
          text-gray-900 dark:text-white
          placeholder-gray-500 dark:placeholder-gray-400
          focus:border-blue-500 dark:focus:border-blue-400 
          focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20
          focus:outline-none"
      />
      {
        isPassword && <button
          type="button"
          className="absolute inset-y-0 right-4 flex items-center text-gray-500 dark:text-gray-400 
          hover:text-gray-700 dark:hover:text-gray-200 transition-colors bg-transparent border-none"
          onClick={() => setShowPassword(!showPassword)}
        >
          {showPassword ? (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
          ) : (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
          )}
        </button>
      }
    </div>
  )
}

export default Input;