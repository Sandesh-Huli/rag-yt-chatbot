import { createContext, useState, useEffect } from "react";

export const AppContext = createContext();
const AppContextProvider = (props)=>{
    const [user,setUser] = useState(null);
    const [authMode,setAuthMode] = useState('signup');
    const [showProfle,setShowProfile] = useState(false);
    const [newChat,setNewChat] = useState(true);
    const [showSidebar, setShowSidebar] = useState(false);
    const [showLogin,setShowLogin] = useState(false);

    // Check for existing user session on mount
    useEffect(() => {
        const token = localStorage.getItem('token');
        const username = localStorage.getItem('username');
        if (token && username) {
            setUser({ username, token });
        }
    }, []);

    // Logout function
    const logout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        setUser(null);
    };
    
    const value = {
        user,setUser,
        authMode,setAuthMode,
        showProfle,setShowProfile,
        showLogin,setShowLogin,
        newChat,setNewChat,
        showSidebar, setShowSidebar,
        logout,
    };
    return (
        <AppContext.Provider value={value}>
            {props.children}
        </AppContext.Provider>
    )
}
export default AppContextProvider;