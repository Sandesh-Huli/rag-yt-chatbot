import { useState, useContext } from 'react'
import Navbar from './components/Navbar.jsx'
import AppContextProvider from './context/AppContext.jsx'
import { AppContext } from './context/AppContext.jsx';

function App() {
  const { showLogin, user, setUser, showProfile } = useContext(AppContext);
  return (
    <>
      <Navbar />
    </>
  )
}

export default App
