import dotenv from "dotenv";
dotenv.config();

import jwt from 'jsonwebtoken'
const JWT_SECRET = process.env.JWT_SECRET;

export default authenticateUser = (req,res,next)=>{
    const authHeader = req.headers.authorization;
    if(!authHeader){
        return res.status(401).json({
            success:false,
            message:"No token provided"
        });
    }
    const token = authHeader.split(".")[1];
    try{
        const decoded = jwt.verify(token,JWT_SECRET);
        req.user = decoded;
        next();             // Attach user info to request
    }catch(err){
        return res.status(401).json({
            success:false,
            message:"Invalid token"
        })
    }
}