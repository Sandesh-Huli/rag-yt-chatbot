import { BrowserRouter } from 'react-router-dom'
import AppContextProvider from './context/AppContext.jsx'
import ChatContextProvider from './context/ChatContext.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <BrowserRouter>
      <AppContextProvider>
        <ChatContextProvider >
          <App />
        </ChatContextProvider >
      </AppContextProvider>
    </BrowserRouter>
  </ErrorBoundary>
)
