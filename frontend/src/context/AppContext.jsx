import { createContext, useState } from "react";

export const AppContext = createContext();
const AppContextProvider = (props)=>{
    const [user,setUser] = useState(null);
    const [authMode,setAuthMode] = useState('signup');
    const [showLogin,setShowLogin] = useState(false);
    const [showProfle,setShowProfile] = useState(false);
    const value = {
        user,setUser,
        authMode,setAuthMode,
        showLogin,setShowLogin,
        showProfle,setShowProfile
    };
    return (
        <AppContext.Provider value={value}>
            {props.children}
        </AppContext.Provider>
    )
}
export default AppContextProvider;