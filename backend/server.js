import dotenv from "dotenv";
dotenv.config();
import app from "./src/app.js";
import { logger } from "./src/logging/structuredLogger.js";

// Validate required environment variables
const requiredEnvVars = [
    'MONGO_URI',
    'JWT_SECRET',
    'SESSION_SECRET',
    'FASTAPI_URL'
];

const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);

if (missingVars.length > 0) {
    logger.error('Missing required environment variables', {
        event_type: 'startup_error',
        missing_vars: missingVars,
    });
    missingVars.forEach(varName => console.error(`   - ${varName}`));
    console.error('\nPlease check your .env file and ensure all required variables are set.');
    console.error('Refer to .env.example for the required configuration.\n');
    process.exit(1);
}

const PORT = process.env.PORT || 4000;

app.listen(PORT, () => {
    logger.info('Environment variables validated successfully', {
        event_type: 'startup',
        port: PORT,
        fastapi_url: process.env.FASTAPI_URL,
    });
})
