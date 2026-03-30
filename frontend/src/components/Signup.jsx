import { useContext, useState } from "react";
import { assets } from "../assets/assets";
import { AppContext } from "../context/AppContext";
import { apiService } from "../services/api";

export default function Signup() {
    const { setShowLogin, setUser } = useContext(AppContext);
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSignup = async (e) => {
        e.preventDefault();
        setError("");

        if (!username.trim()) {
            setError("Username is required");
            return;
        }

        if (!email.trim()) {
            setError("Email is required");
            return;
        }

        if (password !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        if (password.length < 6) {
            setError("Password must be at least 6 characters long");
            return;
        }

        setLoading(true);

        try {
            console.log('Sending signup request...');
            const response = await apiService.signup({ username, email, password });
            console.log('Signup response:', response.data);
            
            if (response.data.success) {
                const token = response.data.token;
                const userName = response.data.user?.username || username;
                localStorage.setItem('token', token);
                localStorage.setItem('username', userName);
                setUser({ username: userName, token });
                setShowLogin(false);
                alert('Signup successful!');
            } else {
                setError(response.data.message || 'Signup failed');
            }
        } catch (err) {
            console.error('Signup error:', err);
            const errorMsg = err.response?.data?.message || 
                           err.message || 
                           'An error occurred during signup. Please try again.';
            setError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full">
            <form className="flex flex-col items-center gap-4" onSubmit={handleSignup}>
                <h3 className="text-2xl text-center text-neutral-700 font-semibold mb-2">Signup</h3>
                {error && <p className="text-red-500 text-sm text-center w-full">{error}</p>}
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
                    disabled={loading}
                    className="w-full mt-4 bg-blue-600 text-white py-2 rounded-full font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                    {loading ? 'Signing up...' : 'Signup'}
                </button>
            </form>
        </div>
    );
}