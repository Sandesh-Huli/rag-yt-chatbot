import { useContext, useState } from "react";
import { assets } from "../assets/assets";
import { AppContext } from "../context/AppContext";

export default function Signup() {
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    return (
        <div className="w-full">
            <form className="flex flex-col items-center gap-4">
                <h3 className="text-2xl text-center text-neutral-700 font-semibold mb-2">Signup</h3>
                <div className="border px-6 py-2 flex items-center gap-2 rounded-full w-full bg-gray-50">
                    <img src={assets.user} alt="username" className="h-6 w-6" />
                    <input
                        type="text"
                        name="username"
                        id="username"
                        placeholder="Enter your username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                        className="bg-transparent outline-none flex-1 text-gray-700"
                    />
                </div>
                <div className="border px-6 py-2 flex items-center gap-2 rounded-full w-full bg-gray-50">
                    <img src={assets.email} alt="email" className="h-6 w-6" />
                    <input
                        type="email"
                        name="email"
                        id="email"
                        placeholder="Enter your email id"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="bg-transparent outline-none flex-1 text-gray-700"
                    />
                </div>
                <div className="border px-6 py-2 flex items-center gap-2 rounded-full w-full bg-gray-50">
                    <img src={assets.padlock} alt="password" className="h-6 w-6" />
                    <input
                        type="password"
                        name="password"
                        id="password"
                        placeholder="Create a password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        className="bg-transparent outline-none flex-1 text-gray-700"
                    />
                </div>
                <div className="border px-6 py-2 flex items-center gap-2 rounded-full w-full bg-gray-50">
                    <img src={assets.padlock} alt="confirm password" className="h-6 w-6" />
                    <input
                        type="password"
                        name="confirmPassword"
                        id="confirmPassword"
                        placeholder="Confirm your password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        className="bg-transparent outline-none flex-1 text-gray-700"
                    />
                </div>
                <button
                    type="submit"
                    className="w-full mt-4 bg-blue-600 text-white py-2 rounded-full font-semibold hover:bg-blue-700 transition-colors"
                >
                    Signup
                </button>
            </form>
        </div>
    );
}