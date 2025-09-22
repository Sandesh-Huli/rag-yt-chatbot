import { useContext } from "react";
import { assets } from "../assets/assets.js"
import { AppContext } from "../context/AppContext.jsx";
import Signup from "./Signup.jsx";
import Login from "./Login.jsx";

export default function Auth() {
    const { authMode, setAuthMode, setShowLogin } = useContext(AppContext);

    const handleClick = () => {
        setAuthMode(authMode === "signup" ? "login" : "signup");
    };

    const handleBackdropClick = (e) => {
        if (e.target === e.currentTarget) {
            setShowLogin(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex justify-center items-center"
            onClick={handleBackdropClick}
        >
            <div className="relative bg-white rounded-xl shadow-2xl p-8 min-w-[350px] max-w-sm w-full flex flex-col items-center">
                <button
                    className="absolute top-4 right-4"
                    onClick={() => setShowLogin(false)}
                    aria-label="Close"
                >
                    <img src={assets.close} alt="close" className="h-5 w-5 cursor-pointer" />
                </button>
                {authMode === "signup" ? <Signup /> : <Login />}
                <div className="w-full">
                    {authMode === 'signup' ? (
                        <p className="text-sm mt-5 text-center text-gray-600">
                            Already have an account?{" "}
                            <span
                                className="text-blue-500 cursor-pointer font-semibold hover:underline"
                                onClick={handleClick}
                            >
                                Login
                            </span>
                        </p>
                    ) : (
                        <p className="text-sm mt-5 text-center text-gray-600">
                            Don't have an account?{" "}
                            <span
                                className="text-blue-500 cursor-pointer font-semibold hover:underline"
                                onClick={handleClick}
                            >
                                Signup
                            </span>
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}