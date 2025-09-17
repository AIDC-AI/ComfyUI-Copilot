
export const enum LocalStorageKeys {
  START_POP_VIEW_AUTO_TIME = 'auto_time',
  START_POP_VIEW_ACCEPT_TIME = 'accept_time',
  MODELS_POP_VIEW_TIME = 'models_time',
  MODELS_POP_VIEW_SELECTED = 'models_selected',
  MODELS_POP_VIEW_LIST = 'models_list'
}

export const getLocalStorage = (key: LocalStorageKeys) => {
  return localStorage.getItem(key as unknown as string);
}

export const setLocalStorage = (key: LocalStorageKeys, value: string) => {
  localStorage.setItem(key as unknown as string, value);
}

export const removeLocalStorage = (key: LocalStorageKeys) => {
  localStorage.removeItem(key as unknown as string);
}

export const clearLocalStorage = () => {
  localStorage.clear();
}