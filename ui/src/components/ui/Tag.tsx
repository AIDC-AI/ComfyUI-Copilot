interface IProps {
  content: string | React.ReactNode
}

const Tag = ({ content }: IProps) => {
  return (
    <div className="inline-block bg-gray-100 rounded-md px-2 py-1 text-sm flex justify-center items-center">
      {content}
    </div>
  )
}

export default Tag;