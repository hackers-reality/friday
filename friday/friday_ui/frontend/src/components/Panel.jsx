import React, { useState, useEffect } from 'react';

export default function Panel({ title, children, delay = 0 }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div className={`panel ${visible ? 'panel-visible' : ''}`}>
      <div className="panel-header">
        <div className="panel-title">{title}</div>
        <div className="panel-line" />
      </div>
      <div className="panel-body">
        {children}
      </div>
      <div className="panel-corner tl" />
      <div className="panel-corner tr" />
      <div className="panel-corner bl" />
      <div className="panel-corner br" />
    </div>
  );
}
