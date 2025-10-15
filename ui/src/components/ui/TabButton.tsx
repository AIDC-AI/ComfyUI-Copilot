const TabButton = ({ 
  active, 
  onClick, 
  children 
}: { 
  active: boolean; 
  onClick: () => void; 
  children: React.ReactNode 
}) => (
  <button
      onClick={onClick}
      className={`px-4 py-2 font-medium text-xs transition-colors duration-200 border-b-2 ${
          active 
              ? "text-[#71A3F2] border-[#71A3F2]" 
              : "text-gray-600 border-transparent hover:!text-[#71A3F2] hover:!border-[#71A3F2]"
      }`}
  >
      {children}
  </button>
);

export default TabButton;