import { ChangeEvent, useRef } from "react";
import { PlusIcon, XIcon } from './Icons';
import { UploadedImage } from "../../types/types";
import ImageLoading from "../ui/Image-Loading";

interface IProps {
  onUploadImages: (files: FileList) => void
  uploadedImages: UploadedImage[]
  onRemoveImage: (imageId: string) => void;
  onClose: () => void
}

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const SUPPORTED_FORMATS = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

const ImageUploadModal: React.FC<IProps> = (props) => {
  const { onUploadImages, uploadedImages, onRemoveImage, onClose } = props

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
        if (uploadedImages?.length >= 3) {
            alert('You can only upload up to 3 images');
            return;
        }

        const invalidFiles: string[] = [];
        const validFiles: File[] = [];

        Array.from(event.target.files).forEach(file => {
            if (!SUPPORTED_FORMATS.includes(file.type)) {
                invalidFiles.push(`${file.name} (unsupported format)`);
            } else if (file.size > MAX_FILE_SIZE) {
                invalidFiles.push(`${file.name} (exceeds 5MB)`);
            } else {
                validFiles.push(file);
            }
        });

        if (invalidFiles.length > 0) {
            alert(`The following files couldn't be uploaded:\n${invalidFiles.join('\n')}`);
        }

        if (uploadedImages?.length + validFiles.length > 3) {
            alert('You can only upload up to 3 images');
            return;
        }

        if (validFiles.length > 0) {
            const dataTransfer = new DataTransfer();
            validFiles.forEach(file => dataTransfer.items.add(file));
            onUploadImages(dataTransfer.files);
        }
    }
  };  
  
  return <div 
    id="comfyui-copilot-image-upload-modal" 
    className="fixed inset-0 bg-[rgba(0,0,0,0.5)] flex items-center justify-center"
    style={{
        backgroundColor: 'rgba(0,0,0,0.5)'
    }}
  >
    <div className="bg-white rounded-lg p-6 w-96 relative">
      <button 
        onClick={onClose}
        className="absolute top-2 right-2 bg-white border-none text-gray-500 hover:!text-gray-700"
      >
        <XIcon className="w-5 h-5" />
      </button>
        
      <h3 className="text-lg text-gray-800 font-medium mb-4">Upload Images</h3>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8
                    flex flex-col items-center justify-center gap-4
                    hover:!border-blue-500 transition-colors cursor-pointer"
          onClick={() => fileInputRef.current?.click()}
        >
          <PlusIcon className="w-8 h-8 text-gray-400" />
            <div className="text-center">
              <p className="text-sm text-gray-500 mb-2">
                  Click to upload images or drag and drop
              </p>
              <p className="text-xs text-gray-400">
                  Supported formats: JPG, PNG, GIF, WebP
              </p>
                <p className="text-xs text-gray-400">
                    Max file size: 5MB, Max 3 images
                </p>
            </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={SUPPORTED_FORMATS.join(',')}
          onChange={handleFileChange}
          className="hidden"
        />

        {/* 预览区域 */}
        {uploadedImages.length > 0 && (
            <div className="mt-4 grid grid-cols-3 gap-2">
                {uploadedImages.map(image => (
                    <div key={image.id} className="relative group">
                        <img 
                            src={image.preview} 
                            alt="preview" 
                            className="w-full h-20 object-contain"
                        />
                        {
                            !!image?.url && image?.url !== '' ? <button
                                onClick={() => onRemoveImage(image.id)}
                                className="absolute -top-1 -right-1 bg-white border-none text-gray-500 rounded-full p-0.5
                                        opacity-0 group-hover:!opacity-100 transition-opacity"
                            >
                                <XIcon className="w-3 h-3" />
                            </button> : <ImageLoading />
                        }
                    </div>
                ))}
            </div>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 
                      bg-white border border-gray-300 rounded-md 
                      hover:!bg-gray-50"
          >
              Close
          </button>
        </div>
    </div>
  </div>
}

export default ImageUploadModal;