import { createContext, useState } from "react";

export const AppContext = createContext();
const AppContextProvider = (props)=>{
    const [user,setUser] = useState(null);
    const [authMode,setAuthMode] = useState('signup');
    const [showProfle,setShowProfile] = useState(false);
    const [newChat,setNewChat] = useState(true);
    const [showSidebar, setShowSidebar] = useState(false);
    const [showLogin,setShowLogin] = useState(false);
    const [video_id,setVideoId] = useState('');
    const value = {
        user,setUser,
        authMode,setAuthMode,
        showProfle,setShowProfile,
        showLogin,setShowLogin,
        newChat,setNewChat,
        showSidebar, setShowSidebar,
        video_id,setVideoId
    };
    return (
        <AppContext.Provider value={value}>
            {props.children}
        </AppContext.Provider>
    )
}
export default AppContextProvider;