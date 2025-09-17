import express from "express";
import { registerUser,loginUser, previewUser } from "../controllers/userController.js";
const router = express.Router();

//register user route
router.post('/register',registerUser);

//login user route
router.post('/login',loginUser);

//show profile route
router.get('/:id',previewUser);
router.get('/',(req,res)=>{
    res.send('users route')
})
export const userRouter = router; 