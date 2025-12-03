import dotenv from "dotenv";
dotenv.config();
import app from "./src/app.js";

// Validate required environment variables
const requiredEnvVars = [
    'MONGO_URI',
    'JWT_SECRET',
    'SESSION_SECRET',
    'FASTAPI_URL'
];

const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);

if (missingVars.length > 0) {
    console.error('❌ Error: Missing required environment variables:');
    missingVars.forEach(varName => console.error(`   - ${varName}`));
    console.error('\nPlease check your .env file and ensure all required variables are set.');
    console.error('Refer to .env.example for the required configuration.\n');
    process.exit(1);
}

const PORT = process.env.PORT || 4000;

app.listen(PORT, () => {
    console.log('✅ Environment variables validated successfully');
    console.log(`🚀 Backend server running on port: ${PORT}`);
    console.log(`📡 FastAPI URL: ${process.env.FASTAPI_URL}`);
})
