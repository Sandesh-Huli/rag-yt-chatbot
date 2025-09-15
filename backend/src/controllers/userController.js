import dotenv from "dotenv";
dotenv.config();

const JWT_SECRET = process.env.JWT_SECRET;

import userModel from "../models/userModel";
import bcrypt from 'bcrypt'
import jwt from 'jsonwebtoken'

export default registerUser = async (req,res)=>{
    try {
        const {email,password,username} = req.body;
        if(!username || !email || !password){
            return res.json({
                success:false,
                message:"Missing details"
            });
        }
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(password,salt);
        const newUserModel = new userModel({
            username:username,email:email,password:hashedPassword
        });
        const newUser = await newUserModel.save();

        const token = jwt.sign({id:newUser._id},JWT_SECRET);
        res.json({
            success:true,
            token:token,
            user:{
                username:user.username
            }
        })
    } catch (error) {
        console.log(error)
        res.json({
            success:false,
            message:error.message
        })
    }
}
