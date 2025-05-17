# Add this function to your existing jwt.py file

def get_current_user_optional(token: str, db: Session):
    """
    Similar to get_current_user but doesn't raise an exception if the token is invalid.
    Returns None instead.
    """
    try:
        # Extract the token from the Authorization header
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            return None
            
        return user
    except:
        return None