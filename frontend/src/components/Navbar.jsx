import { useContext, useState } from 'react';
import logo from '../assets/logo.png'
import sidebar from '../assets/sidebar.png'
import { AppContext } from "../context/AppContext";
import Auth from './Auth.jsx';
export default function Navbar() {
    const {user, setUser, showSidebar, setShowSidebar, authMode, setAuthMode,showLogin,setShowLogin } = useContext(AppContext);
    const handleLoginClick = ()=>{
        //add logic later 
        setShowLogin(!showLogin);
    }
    return (
        <>
            <div className='flex items-center justify-between shadow-md px-6 py-3'>
                <div className='flex items-center gap-5'>
                    <img src={sidebar} alt="sidebar" className='h-8 w-8 cursor-pointer hover:scale-110 transition-transform duration-200' onClick={()=>setShowSidebar(!showSidebar)}/>
                    <img src={logo} alt="logo" className='w-12 h-12 object-contain cursor-pointer ' />
                    <div className='ml-2'>
                        <h1 className='text-xl font-bold text-gray-800'>RAG YT CHATBOT</h1>
                        <p className='text-sm text-gray-500'>Analyze and discuss video with AI</p>
                    </div>
                </div>
                <div className='auth '>
                    <button className="bg-zinc-800 text-white px-5 py-2 rounded-md sm:px-10 " onClick={handleLoginClick}>
                                {showLogin === false ? 'Sign Up' : 'Login'}
                    </button>
                </div>
                {
                    showLogin && <Auth />
                }
            </div>
        </>
    )
    
}