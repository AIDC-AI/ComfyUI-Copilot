import { useEffect, useState } from "react";
import useLanguage from "../../hooks/useLanguage";
import { github_url } from "../../config";
import { getLocalStorage, LocalStorageKeys, setLocalStorage } from "../../utils/localStorageManager";
import logoImage from '../../../../assets/logo.png';
import gifImage from '../../../../assets/gif.gif';
import { Portal } from "../chat/Portal";
import ButtonClose from "./ButtonClose";

export const ACCEPT_EVENT = 'accept_event'

const enum TIME_KEY {
  AUTO = 'auto',
  ACCEPT = 'accept'
}

const TIME_MAP = {
  [TIME_KEY.AUTO]: {
    name: LocalStorageKeys.START_POP_VIEW_AUTO_TIME,
    offset: 1000 * 60 * 60 * 24 * 3 // 3 days
  },
  [TIME_KEY.ACCEPT]: {
    name: LocalStorageKeys.START_POP_VIEW_ACCEPT_TIME,
    offset: 1000 * 60 * 60 * 24 * 1 // 1 days
  }
}

const StartPopView = () => {
  const { startpopview_title, startpopview_join } = useLanguage()
  
  const [showModal, setShowModal] = useState<boolean>(false);
  
  const handleClickStar = () => {
    setShowModal(!showModal);
  }

  const handleClickJoin = () => {
    window.open(github_url, '_blank');
    setShowModal(false);
  }

  const checkTime = (key: TIME_KEY) => {
    const { name, offset } = TIME_MAP[key]
    const currentTime = new Date().getTime()
    const time = getLocalStorage(name);
    if (!time || (!!Number(time) && currentTime - Number(time) > offset)) {
      setLocalStorage(name, currentTime.toString());
      setShowModal(true);
    }
  }

  useEffect(() => {
    checkTime(TIME_KEY.AUTO);

    const handleClickAccept = () => {
      checkTime(TIME_KEY.ACCEPT);
    }

    window.addEventListener(ACCEPT_EVENT, handleClickAccept);

    return () => {
        window.removeEventListener(ACCEPT_EVENT, handleClickAccept);
    }
  }, [])

  return (
    <Portal className="pointer-events-none">
      <div id="comfyui-copilot-start-pop-view">
        {/* <button 
          className="fixed !left-auto !top-auto right-16 bottom-4 text-gray-700"
          onClick={handleClickStar}
        >
          <svg viewBox="0 0 1026 1024" className="w-8 h-8" fill='currentColor'>
            <path d="M687.216531 703.699954l-148.871852 302.254973c-7.51878 15.037561-27.06761 22.556341-42.105171 15.037561-6.015024-3.007512-12.030049-7.51878-15.03756-15.037561l-148.871853-302.254973c-3.007512-6.015024-7.51878-12.030049-15.037561-15.037561L18.045073 541.294296c-15.037561-7.51878-22.556341-27.06761-15.037561-42.10517 3.007512-6.015024 7.51878-12.030049 15.037561-15.037561l302.254973-148.871852c6.015024-3.007512 12.030049-7.51878 15.037561-15.037561l148.871853-302.254974c7.51878-15.037561 27.06761-22.556341 42.10517-15.03756 6.015024 3.007512 12.030049 7.51878 15.037561 15.03756l148.871853 302.254974c3.007512 6.015024 7.51878 12.030049 15.03756 15.037561L1007.516578 484.151565c15.037561 7.51878 22.556341 27.06761 15.037561 42.105171-3.007512 6.015024-7.51878 12.030049-15.037561 15.03756l-302.254974 148.871853c-9.022537 1.503756-15.037561 7.51878-18.045073 13.533805z">
            </path>
          </svg>
        </button> */}
        {
          showModal && (
            <div
              className="fixed !left-auto !top-auto right-2 bottom-2 text-gray-700 w-[300px] h-[280px] bg-white border border-gray-600 rounded-[12px] flex flex-col justify-center shadow-[inset_0_0_12px_2px_#3b82f6] shadow-[inset_0_0_0_4px_rgba(59,130,246,0.15)] pointer-events-auto"
            >
              <div className="flex-1">
                {/* <svg viewBox="0 0 1024 1024" className="w-8 h-8 mt-4 ml-4" fill="#FFD700">
                  <path d="M823.466667 322.133333a18.005333 18.005333 0 0 1-9.088-2.133333 14.250667 14.250667 0 0 1-5.845334-7.466667l-30.933333-72.533333-77.866667-34.133333a14.250667 14.250667 0 0 1-7.466666-5.888 17.962667 17.962667 0 0 1-2.133334-9.045334c0-3.541333 0.725333-6.570667 2.133334-9.045333a14.250667 14.250667 0 0 1 7.466666-5.888l77.866667-33.066667 30.933333-69.333333a14.250667 14.250667 0 0 1 5.845334-7.466667 18.005333 18.005333 0 0 1 9.088-2.133333c3.541333 0 6.570667 0.725333 9.045333 2.133333a14.293333 14.293333 0 0 1 5.888 7.466667l30.933333 69.333333 77.866667 33.066667c3.541333 1.408 6.058667 3.413333 7.466667 5.888 1.408 2.474667 2.133333 5.504 2.133333 9.045333a18.005333 18.005333 0 0 1-2.133333 9.088 14.293333 14.293333 0 0 1-7.466667 5.845334l-77.866667 34.133333-30.933333 72.533333a14.293333 14.293333 0 0 1-5.845333 7.466667 18.005333 18.005333 0 0 1-9.088 2.133333z m0 635.733334a18.944 18.944 0 0 1-8.533334-2.133334 13.482667 13.482667 0 0 1-6.4-7.466666l-30.933333-69.333334-76.8-33.066666a14.250667 14.250667 0 0 1-7.466667-5.845334 17.962667 17.962667 0 0 1-2.133333-9.088c0-3.541333 0.725333-6.570667 2.133333-9.088a14.250667 14.250667 0 0 1 7.466667-5.845333l76.8-33.066667 30.933333-73.6a14.250667 14.250667 0 0 1 5.845334-7.466666 18.005333 18.005333 0 0 1 9.088-2.133334c3.541333 0 6.570667 0.725333 9.045333 2.133334a14.293333 14.293333 0 0 1 5.888 7.466666l30.933333 73.6 76.8 33.066667c3.541333 1.408 6.058667 3.413333 7.466667 5.845333 1.408 2.517333 2.133333 5.546667 2.133333 9.088a18.005333 18.005333 0 0 1-2.133333 9.045334 14.293333 14.293333 0 0 1-7.466667 5.888l-76.8 33.066666-30.933333 69.333334a13.525333 13.525333 0 0 1-6.4 7.466666 18.986667 18.986667 0 0 1-8.533333 2.133334zM355.2 773.333333a31.701333 31.701333 0 0 1-16.554667-4.821333 31.786667 31.786667 0 0 1-12.245333-13.312l-69.333333-148.266667-149.333334-67.2a31.786667 31.786667 0 0 1-13.354666-12.245333 31.744 31.744 0 0 1-4.778667-16.554667c0-5.674667 1.578667-11.178667 4.778667-16.512a31.786667 31.786667 0 0 1 13.354666-12.288l149.333334-67.2 69.333333-147.2a31.701333 31.701333 0 0 1 28.8-19.2c5.674667 0 11.178667 1.578667 16.512 4.778667 5.333333 3.2 9.429333 7.68 12.288 13.354667l70.4 148.266666 148.266667 67.2c6.4 2.858667 11.178667 6.912 14.421333 12.245334a31.744 31.744 0 0 1 4.778667 16.554666 31.744 31.744 0 0 1-19.2 28.8l-148.266667 67.2L384 755.2a27.818667 27.818667 0 0 1-12.288 13.866667 34.688 34.688 0 0 1-16.512 4.266666z">
                  </path>
                </svg> */}
                <div className="w-full flex justify-between items-center">
                  <img 
                      src={`.${logoImage}`}
                      alt="ComfyUI-Copilot Logo" 
                      className="w-16 h-16" 
                  />
                  <div className="w-16 h-16 flex justify-center items-center">
                    <ButtonClose 
                      onClose={() => setShowModal(false)}
                    />
                  </div>
                </div>
                <div className="text-gray-700 text-sm text-center whitespace-pre-line">
                  {startpopview_title}
                </div>
                <img 
                  src={`.${gifImage}`}
                  className="w-20 h-20 mt-2 mx-auto block"
                />
              </div>
              <button
                className="bg-gray-100 rounded-md flex justify-center items-center w-[240px] h-[40px] mx-[30px] mb-4"
                onClick={handleClickJoin}
              >
                <span className="text-gray-900 text-sm">
                  {startpopview_join}
                </span>
              </button>
            </div>
          )
        }
      </div>
    </Portal>
  )
}

export default StartPopView;