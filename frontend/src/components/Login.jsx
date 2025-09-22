import { useState } from "react";
import { assets } from "../assets/assets";

export default function Login() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    return (
        <div className="w-full">
            <form className="flex flex-col items-center gap-4">
                <h3 className="text-2xl text-center text-neutral-700 font-semibold mb-2">Login</h3>
                <div className="border px-6 py-2 flex items-center gap-2 rounded-full w-full bg-gray-50">
                    <img src={assets.email} alt="email" className="h-6 w-6" />
                    <input
                        type="email"
                        name="email"
                        id="email"
                        placeholder="Enter your email"
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
                        placeholder="Enter your password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        className="bg-transparent outline-none flex-1 text-gray-700"
                    />
                </div>
                <button
                    type="submit"
                    className="w-full mt-4 bg-blue-600 text-white py-2 rounded-full font-semibold hover:bg-blue-700 transition-colors"
                >
                    Login
                </button>
            </form>
        </div>
    )
}