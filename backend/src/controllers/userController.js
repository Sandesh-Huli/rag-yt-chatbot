import dotenv from "dotenv";
dotenv.config();

const JWT_SECRET = process.env.JWT_SECRET;

import userModel from "../models/userModel.js";
import bcrypt from 'bcrypt'
import jwt from 'jsonwebtoken'

export const registerUser = async (req,res)=>{
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
                username:newUser.username
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
export const loginUser = async(req,res)=>{
    try {
        const {email,password} = req.body;
        if(!email || !password){
            return res.json({
                success:false,
                message:"Missing details"
            });
        }
        const user = await userModel.findOne({email:email})
        if(!user){
            return res.json({
                success:false,
                message:"User doesn't exist"
            })
        }
        const isMatch = await bcrypt.compare(password,user.password);
        if(isMatch){
            const token = jwt.sign({id:user._id},JWT_SECRET);
            return res.json({
                success:true,
                token:token,
                message:"Login successful"
            })
        }else{
            return res.json({
                success:false,
                message:"Incorrect password"
            })
        }
    } catch (error) {
        console.log(error)
        return res.json({
            success:false,
            message:error.message
        });
    }
}
export const previewUser = async(req,res)=>{
    try{
        const id = req.params.id;
        if(!id){
            return res.json({success:false,message:"User id not found"});
        }
        const user =  await userModel.findOne({_id:id});
        if(!user){
            return res.json({success:false,message:"User not found"});
        }
        return res.json({
            success:true,
            user:user,
            message:"User profile"
        })
    }catch(err){
        return res.json({
            success:false,
            message:err.message
        });
    }
}
