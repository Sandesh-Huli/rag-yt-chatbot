import dotenv from "dotenv";
dotenv.config();

const JWT_SECRET = process.env.JWT_SECRET;

import userModel from "../models/userModel.js";
import bcrypt from 'bcrypt'
import jwt from 'jsonwebtoken'
import { logger, auditLogger } from "../logging/structuredLogger.js";

export const registerUser = async (req,res)=>{
    try {
        const {email,password,username} = req.body;
        
        if(!username || !email || !password){
            // Log unsuccessful registration attempt (Issue 34)
            auditLogger.logAuthAttempt({
                email: email || 'unknown',
                action: 'register',
                success: false,
                ipAddress: req.ip,
                userAgent: req.get('user-agent'),
                error: 'Missing required fields',
            });
            
            return res.json({
                success:false,
                message:"Missing details"
            });
        }

        // Check if user already exists
        const existingUser = await userModel.findOne({ email });
        if (existingUser) {
            // Log duplicate registration attempt (Issue 34)
            auditLogger.logAuthAttempt({
                email,
                action: 'register',
                success: false,
                ipAddress: req.ip,
                userAgent: req.get('user-agent'),
                error: 'User already exists',
            });
            
            return res.status(400).json({
                success: false,
                message: "User with this email already exists"
            });
        }

        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(password,salt);
        const newUserModel = new userModel({
            username:username,email:email,password:hashedPassword
        });
        const newUser = await newUserModel.save();  
        
        const token = jwt.sign({id:newUser._id},JWT_SECRET);
        
        // Log successful registration (Issue 34)
        auditLogger.logAuthAttempt({
            email,
            action: 'register',
            success: true,
            ipAddress: req.ip,
            userAgent: req.get('user-agent'),
        });
        
        logger.info('User registered successfully', {
            event_type: 'user_registration',
            username,
            email,
            user_id: newUser._id.toString(),
        });
        
        return res.json({
            success:true,
            token:token,
            user:{
                username:newUser.username
            }
        })
    } catch (error) {
        logger.error('Registration error', {
            event_type: 'registration_error',
            error_message: error.message,
            error_type: error.name,
            email: req.body.email,
            ip_address: req.ip,
        });
        
        // Log registration failure (Issue 34)
        auditLogger.logAuthAttempt({
            email: req.body.email || 'unknown',
            action: 'register',
            success: false,
            ipAddress: req.ip,
            userAgent: req.get('user-agent'),
            error: error.message,
        });
        
        return res.status(500).json({
            success:false,
            message: error.code === 11000 ? 'Email already exists' : error.message
        })
    }
}

export const loginUser = async(req,res)=>{
    try {
        const {email,password} = req.body;
        
        if(!email || !password){
            // Log login attempt with missing credentials (Issue 34)
            auditLogger.logAuthAttempt({
                email: email || 'unknown',
                action: 'login',
                success: false,
                ipAddress: req.ip,
                userAgent: req.get('user-agent'),
                error: 'Missing credentials',
            });
            
            return res.json({
                success:false,
                message:"Missing details"
            });
        }
        
        const user = await userModel.findOne({email:email})
        
        if(!user){
            // Log failed login - user not found (Issue 34)
            auditLogger.logAuthAttempt({
                email,
                action: 'login',
                success: false,
                ipAddress: req.ip,
                userAgent: req.get('user-agent'),
                error: 'User not found',
            });
            
            logger.warning('Login attempt for non-existent user', {
                event_type: 'login_failure',
                reason: 'user_not_found',
                email,
                ip_address: req.ip,
            });
            
            return res.json({
                success:false,
                message:"User doesn't exist"
            })
        }
        
        const isMatch = await bcrypt.compare(password,user.password);
        
        if(isMatch){
            const token = jwt.sign({id:user._id},JWT_SECRET);
            
            // Log successful login (Issue 34)
            auditLogger.logAuthAttempt({
                email,
                action: 'login',
                success: true,
                ipAddress: req.ip,
                userAgent: req.get('user-agent'),
            });
            
            logger.info('User logged in successfully', {
                event_type: 'user_login',
                user_id: user._id.toString(),
                email,
            });
            
            return res.json({
                success:true,
                token:token,
                username:user.username,
                message:"Login successful"
            })
        } else {
            // Log failed login - incorrect password (Issue 34)
            auditLogger.logAuthAttempt({
                email,
                action: 'login',
                success: false,
                ipAddress: req.ip,
                userAgent: req.get('user-agent'),
                error: 'Incorrect password',
            });
            
            logger.warning('Failed login attempt - incorrect password', {
                event_type: 'login_failure',
                reason: 'incorrect_password',
                email,
                ip_address: req.ip,
            });
            
            return res.json({
                success:false,
                message:"Incorrect password"
            })
        }
    } catch (error) {
        logger.error('Login error', {
            event_type: 'login_error',
            error_message: error.message,
            error_type: error.name,
            email: req.body.email,
            ip_address: req.ip,
        });
        
        // Log login failure (Issue 34)
        auditLogger.logAuthAttempt({
            email: req.body.email || 'unknown',
            action: 'login',
            success: false,
            ipAddress: req.ip,
            userAgent: req.get('user-agent'),
            error: error.message,
        });
        
        return res.status(500).json({
            success:false,
            message:error.message
        });
    }
}

export const previewUser = async(req,res)=>{
    try{
        const id = req.params.id;
        if(!id){
            // Log failed profile access (Issue 34)
            auditLogger.logResourceAccess({
                resource: `/user/${id || 'unknown'}`,
                action: 'read',
                success: false,
                ipAddress: req.ip,
                error: 'User id not found',
            });
            
            return res.json({success:false,message:"User id not found"});
        }
        
        const user = await userModel.findOne({_id: id});
        if(!user){
            // Log failed profile access (Issue 34)
            auditLogger.logResourceAccess({
                user_id: id,
                resource: `/user/${id}`,
                action: 'read',
                success: false,
                ipAddress: req.ip,
                error: 'User not found',
            });
            
            logger.warning('Profile access - user not found', {
                event_type: 'resource_access_failure',
                resource: `/user/${id}`,
                ip_address: req.ip,
            });
            
            return res.json({success:false, message:"User not found"});
        }
        
        // Log successful profile access (Issue 34)
        auditLogger.logResourceAccess({
            user_id: id,
            resource: `/user/${id}`,
            action: 'read',
            success: true,
            ipAddress: req.ip,
        });
        
        logger.info('User profile accessed', {
            event_type: 'resource_access',
            resource: `/user/${id}`,
            user_id: id,
        });
        
        return res.json({
            success: true,
            user: user,
            message: "User profile"
        });
    } catch(err) {
        logger.error('Profile access error', {
            event_type: 'resource_access_error',
            error_message: err.message,
            error_type: err.name,
            user_id: req.params.id,
            ip_address: req.ip,
        });
        
        // Log profile access error (Issue 34)
        auditLogger.logResourceAccess({
            user_id: req.params.id,
            resource: `/user/${req.params.id}`,
            action: 'read',
            success: false,
            ipAddress: req.ip,
            error: err.message,
        });
        
        return res.json({
            success: false,
            message: err.message
        });
    }
}
