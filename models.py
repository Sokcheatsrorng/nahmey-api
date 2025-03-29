from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime

class ReviewVoteType(str, Enum):
    HELPFUL = "helpful"
    UNHELPFUL = "unhelpful"

class ReviewReportReason(str, Enum):
    INAPPROPRIATE = "inappropriate"
    SPAM = "spam"
    FAKE = "fake"
    OFFENSIVE = "offensive"
    OTHER = "other"

class ReviewVote(BaseModel):
    id: str
    user_id: str
    rating_id: str
    vote_type: ReviewVoteType
    created_at: datetime
    
    class Config:
        orm_mode = True

class ReviewVoteCreate(BaseModel):
    vote_type: ReviewVoteType


class ReviewCreate(BaseModel):
    user_id: str
    restaurant_id: str
    rating: float
    review_text: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    has_response: bool = False
    
    @validator("created_at", "updated_at", pre=True, always=True)
    def set_dates(cls, v):
        return v or datetime.now()
    
    @validator("rating")
    def validate_rating(cls, value):
        if value < 1 or value > 5:
            raise ValueError("Rating must be between 1 and 5")
        return value

class ReviewReport(BaseModel):
    id: str
    user_id: str
    rating_id: str
    reason: ReviewReportReason
    description: Optional[str] = None
    status: str = "pending"  # pending, reviewed, dismissed
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class ReviewReportCreate(BaseModel):
    reason: ReviewReportReason
    description: Optional[str] = None

class ReviewResponse(BaseModel):
    id: str
    rating_id: str
    user_id: str
    response_text: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class ReviewResponseCreate(BaseModel):
    response_text: str

class ReviewAnalytics(BaseModel):
    total_reviews: int
    average_rating: float
    rating_distribution: Dict[str, int]  # e.g., {"1": 5, "2": 10, ...}
    recent_trend: float  # change in average rating over last 30 days
    most_mentioned_keywords: List[Dict[str, Any]]  # e.g., [{"word": "spicy", "count": 5}, ...]

class ReviewFilterParams(BaseModel):
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sort_by: Optional[str] = "recent"  # recent, highest, lowest, most_helpful
    has_response: Optional[bool] = None
    keywords: Optional[List[str]] = None
    
    class Config:
        orm_mode = True

class Review(BaseModel):
    id: str
    user_id: str
    restaurant_id: str
    rating: float
    review_text: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    has_response: bool = False
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "12345",
                "user_id": "67890",
                "restaurant_id": "54321",
                "rating": 4.5,
                "review_text": "Great food and service!",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "helpful_votes": 10,
                "unhelpful_votes": 2,
                "has_response": True
            }
        }
    @validator("rating")
    def validate_rating(cls, value):
        if value < 1 or value > 5:
            raise ValueError("Rating must be between 1 and 5")
        return value
    @validator("review_text")
    def validate_review_text(cls, value):
        if len(value) < 10:
            raise ValueError("Review text must be at least 10 characters long")
        return value
    @validator("review_text")
    def validate_review_text_length(cls, value):
        if len(value) > 500:
            raise ValueError("Review text must be at most 500 characters long")
        return value
    @validator("created_at", "updated_at")
    def validate_dates(cls, value):
        if not isinstance(value, datetime):
            raise ValueError("Date must be a valid datetime object")
        return value
    @validator("helpful_votes", "unhelpful_votes")
    def validate_votes(cls, value):
        if value < 0:
            raise ValueError("Votes must be a non-negative integer")
        return value
    @validator("has_response")
    def validate_has_response(cls, value):
        if not isinstance(value, bool):
            raise ValueError("has_response must be a boolean")
        return value
    @validator("restaurant_id")
    def validate_restaurant_id(cls, value):
        if not isinstance(value, str):
            raise ValueError("restaurant_id must be a string")
        return value
    @validator("user_id")       
    def validate_user_id(cls, value):
        if not isinstance(value, str):
            raise ValueError("user_id must be a string")
        return value

# class ReviewVoteUpdate(BaseModel):
#     vote_type: Optional[ReviewVoteType] = None
#     created_at: Optional[datetime] = None
#     user_id: Optional[str] = None
#     rating_id: Optional[str] = None

#     @validator("created_at", pre=True, always=True)
#     def set_created_at(cls, v):
#         return v or datetime.now()

#     @validator("vote_type")
#     def validate_vote_type(cls, value):
#         if value not in [ReviewVoteType.HELPFUL, ReviewVoteType.UNHELPFUL]:
#             raise ValueError("vote_type must be either 'helpful' or 'unhelpful'")
#         return value

#     class Config:
#         from_attributes = True