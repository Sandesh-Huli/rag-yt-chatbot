import dotenv from "dotenv";
dotenv.config();
const MONGO_URI = process.env.MONGO_URI;
import mongoose from "mongoose";

async function main() {
    await mongoose.connect(MONGO_URI);
}
main()
.then(()=>{
    console.log('Connected to the yt_chatbot database');
})
.catch((Error)=>{
    console.log('Error connecting to the database');
    console.log(Error);
})

export default main;