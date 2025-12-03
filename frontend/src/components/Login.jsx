import { useState, useContext } from "react";
import { assets } from "../assets/assets";
import { apiService } from "../services/api";
import { AppContext } from "../context/AppContext";

export default function Login() {
    const { setShowLogin, setUser } = useContext(AppContext);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleLogin = async (e) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const response = await apiService.login({ email, password });
            
            if (response.data.success) {
                const username = response.data.username || email;
                const token = response.data.token;
                localStorage.setItem('token', token);
                localStorage.setItem('username', username);
                setUser({ username, token });
                setShowLogin(false);
                alert('Login successful!');
            } else {
                setError(response.data.message || 'Login failed');
            }
        } catch (err) {
            setError(err.response?.data?.message || 'An error occurred during login');
        } finally {
            setLoading(false);
        }
    };
    return (
        <div className="w-full">
            <form className="flex flex-col items-center gap-4" onSubmit={handleLogin}>
                <h3 className="text-2xl text-center text-neutral-700 font-semibold mb-2">Login</h3>
                {error && <p className="text-red-500 text-sm text-center w-full">{error}</p>}
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
                    disabled={loading}
                    className="w-full mt-4 bg-blue-600 text-white py-2 rounded-full font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                    {loading ? 'Logging in...' : 'Login'}
                </button>
            </form>
        </div>
    )
}