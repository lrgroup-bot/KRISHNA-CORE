import React from 'react';
import ReactDOM from 'react-dom/client';
import 'dockview-react/dist/styles/dockview.css';
import '@xyflow/react/dist/style.css';
import '@xterm/xterm/css/xterm.css';
import './styles.css';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
