import questions from '../../../constants/questions.json'
import { useChatContext } from '../../../context/ChatContext';
import { Message } from '../../../types/types';
import { generateUUID } from '../../../utils/uuid';
import { BaseMessage } from './BaseMessage';

const QuestionTitleMessage: React.FC = () => {
  const { dispatch } = useChatContext();

  const addQuestion = (question: string) => {
    const message: Message = {
      id: generateUUID(),
      role: "user",
      content: question
    };
    dispatch({ type: 'ADD_MESSAGE', payload: message });
    dispatch({ type: 'SET_LOADING', payload: true });
  }

  const addAnswer = (answer: string) => {
    dispatch({ type: 'SET_LOADING', payload: false });
    const offset = 2;
    let end = 0;
    const aiMessageId = generateUUID();
    const func = (isFirst: boolean = false) => {
      end += offset
      const content = answer.slice(0, end);
      const message = {
        id: aiMessageId,
        role: "ai",
        content: JSON.stringify({
          text: content
        }),
        finished: false,
        name: "Assistant"
      }
      if (end > answer.length) {
        message.finished = true
      } else {
        setTimeout(() => {
          func()
        }, 50)
      }
      const type = isFirst ? 'ADD_MESSAGE' : 'UPDATE_MESSAGE';
      dispatch({ type, payload: message });
    }
    func(true)
  }

  return <BaseMessage name='questionTitle'>
    <div className='bg-gray-100 p-4 rounded-lg'>
      <div className='text-base text-gray-900 font-medium'>
        welcome to ComfyUI Copilot! This is a question user message component.
      </div>
      {
        questions.map((item, index) => <div 
          className='flex mt-2'
          key={index.toString()}
          onClick={() => {
            addQuestion(item.question);
            setTimeout(() => {
              addAnswer(item.answer);
            }, 1000);
          }}
        >
          <span className='text-sm text-gray-900 font-normal border border-gray-900 rounded-md px-2 py-1'>
            {item.question}
          </span>
        </div>)
      }
    </div>
  </BaseMessage>
}

export default QuestionTitleMessage;