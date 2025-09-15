import { useState, useEffect } from 'react';

const useDarkTheme = () => {
  const [isDark, setIsDark] = useState(() => 
    document.body.classList.contains('dark-theme')
  );

  useEffect(() => {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
          const target = mutation.target as HTMLElement;
          if (target === document.body) {
            setIsDark(target.classList.contains('dark-theme'));
          }
        }
      });
    });

    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  return isDark;
}

export default useDarkTheme;