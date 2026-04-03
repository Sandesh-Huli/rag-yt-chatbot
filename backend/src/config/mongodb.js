import dotenv from "dotenv";
dotenv.config();

const MONGO_URI = process.env.MONGO_URI;
import mongoose from "mongoose";

// ============= Mongoose Singleton Connection Pool =============
// Thread-safe singleton ensuring only one mongoose connection is created and reused.
// Configuration:
// - maxPoolSize=50: Handle up to 50 concurrent requests
// - minPoolSize=10: Keep 10 idle connections ready
// - serverSelectionTimeoutMS=10000: Connection timeout

let mongooseConnection = null;
let connectionPromise = null;

async function getMongooseConnection() {
    // Return existing connection if already established
    if (mongooseConnection && mongooseConnection.connection.readyState === 1) {
        return mongooseConnection;
    }
    
    // Return pending connection promise if connection is in progress
    if (connectionPromise) {
        return connectionPromise;
    }
    
    // Create new connection
    connectionPromise = mongoose.connect(MONGO_URI, {
        maxPoolSize: 50,                    // Max concurrent connections
        minPoolSize: 10,                    // Min idle connections
        serverSelectionTimeoutMS: 10000,    // Connection timeout
        socketTimeoutMS: 45000,             // Socket timeout
        retryWrites: true,                  // Automatic retry on transient errors
        w: 1,                               // Write concern
    })
    .then(() => {
        mongooseConnection = mongoose;
        console.log('✅ MongoDB connection pool established (maxPoolSize=50, minPoolSize=10)');
        connectionPromise = null; // Reset promise after successful connection
        return mongoose;
    })
    .catch((error) => {
        console.error('❌ Error connecting to MongoDB:', error.message);
        connectionPromise = null; // Reset promise on error
        throw error;
    });
    
    return connectionPromise;
}

async function disconnectDB() {
    """Gracefully disconnect from MongoDB connection pool."""
    if (mongooseConnection) {
        try {
            await mongoose.connection.close();
            mongooseConnection = null;
            connectionPromise = null;
            console.log('🗑️ MongoDB connection pool closed');
        } catch (error) {
            console.error('Error closing MongoDB connection:', error);
        }
    }
}

// Initialize connection on import
const main = async () => {
    try {
        await getMongooseConnection();
    } catch (error) {
        console.log('Failed to initialize MongoDB connection');
        console.log(error);
    }
};

main();

// Handle graceful shutdown on process termination
process.on('SIGINT', async () => {
    await disconnectDB();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    await disconnectDB();
    process.exit(0);
});

export { getMongooseConnection, disconnectDB, main };
export default main;