import useDarkMode from '../../hooks/useDarkTheme';

interface IProps {
  children?: React.ReactNode;
  className?: string;
  borderClassName?: string;
}

const BeautifyCard: React.FC<IProps> = ({ children, className, borderClassName }) => {
  const isDark = useDarkMode()
  return (
    <div className='sticky w-full'>
      <div className={`relative ${className || ''} ${isDark ? 'beautify-card-dark' : 'beautify-card-light'}`}>
        <div className={`card-border ${borderClassName || ''}`}/>
        {
          children
        }
      </div>
    </div>
  );
};

export default BeautifyCard;