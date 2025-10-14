import { useContext, useState } from 'react'
import AppContextProvider from './context/AppContext.jsx'
import { AppContext } from './context/AppContext.jsx';
import Navbar from './components/Navbar.jsx'
import Sidebar from './components/Sidebar.jsx'
import Body from './components/Body.jsx';

export default function App() {
  const { showSidebar } = useContext(AppContext);
  return (
    <>
      <Navbar />
      <div className="flex transition-all duration-300">
        {showSidebar && <Sidebar />}
        <div className={showSidebar === true ? "flex-1 ml-0 md:ml-0 transition-all duration-300" : "flex-1 transition-all duration-300"}>
          <Body />
        </div>
      </div>
    </>
  )
}
