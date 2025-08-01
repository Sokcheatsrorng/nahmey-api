from getpass import getuser
from fastapi import FastAPI, Query, HTTPException, Depends, status, Body, Path, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, validator
from uuid import uuid4
from fastapi import HTTPException, status, Depends
from typing import List
from enum import Enum
import random
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import uuid
from typing import Union
import json

# Add these imports at the top of the file, after the existing imports
from models import (
    Review, ReviewCreate, ReviewVote, ReviewVoteCreate, ReviewReport, ReviewReportCreate,
    ReviewResponse, ReviewResponseCreate, ReviewAnalytics, ReviewFilterParams,
    ReviewVoteType, ReviewReportReason
)
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re
from collections import Counter

# Add these imports at the top of the file, after the existing imports:
from fastapi import File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
import os
from file_storage import (
    save_upload_file, delete_file, get_file_metadata, 
    get_files_by_category, get_files_by_related_id, get_files_by_user,
    FileMetadata
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create the FastAPI app
app = FastAPI(
    title="Nhame EY API",
    description="An API for getting personalized food recommendations, restaurant listings, and more",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple test route
@app.get("/")
async def root():
    return {"message": "API is working"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
# Security configuration
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Define enums for categories
class Cuisine(str, Enum):
    ITALIAN = "italian"
    MEXICAN = "mexican"
    CHINESE = "chinese"
    JAPANESE = "japanese"
    INDIAN = "indian"
    AMERICAN = "american"
    CAMBODIAN = "kh"
    MEDITERRANEAN = "mediterranean"
    FRENCH = "french"
    KOREAN = "korean"

class DietaryPreference(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    NONE = "none"

class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    DESSERT = "dessert"

class ItemCategory(str, Enum):
    FOOD = "food"
    DRINK = "drink"
    DESSERT = "dessert"
    APPETIZER = "appetizer"
    SIDE = "side"

class DrinkType(str, Enum):
    WATER = "water"
    SODA = "soda"
    JUICE = "juice"
    COFFEE = "coffee"
    TEA = "tea"
    SMOOTHIE = "smoothie"
    ALCOHOLIC = "alcoholic"
    NON_ALCOHOLIC = "non_alcoholic"

class PriceRange(str, Enum):
    INEXPENSIVE = "$"
    MODERATE = "$$"
    EXPENSIVE = "$$$"
    VERY_EXPENSIVE = "$$$$"

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class Language(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"

class SortOption(str, Enum):
    RELEVANCE = "relevance"
    RATING = "rating"
    TRENDING = "trending"
    PRICE_LOW = "price_low"
    PRICE_HIGH = "price_high"
    NEWEST = "newest"

# Define models
class UserPreferences(BaseModel):
    language: Language = Language.ENGLISH
    dark_mode: bool = False
    dietary_preferences: List[DietaryPreference] = []
    favorite_cuisines: List[Cuisine] = []
    price_range_preference: Optional[List[PriceRange]] = None

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, confirm_password, values):
        if "password" in values and confirm_password != values["password"]:
            raise ValueError("Passwords do not match")
        return confirm_password

class User(UserBase):
    id: str
    role: UserRole
    created_at: datetime
    preferences: UserPreferences
    
    class Config:
        orm_mode = True

class UserInDB(User):
    hashed_password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    preferences: Optional[UserPreferences] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None

class Rating(BaseModel):
    id: str
    user_id: str
    food_item_id: Optional[str] = None
    restaurant_id: Optional[str] = None
    rating: float  # 1-5 stars
    review: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @validator('rating')
    def rating_must_be_valid(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v
    
    class Config:
        orm_mode = True

class RatingCreate(BaseModel):
    food_item_id: Optional[str] = None
    restaurant_id: Optional[str] = None
    rating: float
    review: Optional[str] = None
    
    @validator('rating')
    def rating_must_be_valid(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class RatingUpdate(BaseModel):
    rating: Optional[float] = None
    review: Optional[str] = None
    
    @validator('rating')
    def rating_must_be_valid(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Rating must be between 1 and 5')
        return v

class FoodItemBase(BaseModel):
    name: str
    description: str
    cuisine: Cuisine
    category: ItemCategory = ItemCategory.FOOD
    drink_type: Optional[DrinkType] = None
    dietary_preferences: List[DietaryPreference]
    meal_types: List[MealType]
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    ingredients: List[str]
    cooking_instructions: List[str]
    preparation_time_minutes: Optional[int] = None
    image_url: Optional[str] = None
    
    @validator('drink_type')
    def validate_drink_type(cls, v, values):
        if values.get('category') == ItemCategory.DRINK and v is None:
            raise ValueError('Drink type is required for drink items')
        return v

class FoodItemCreate(FoodItemBase):
    pass

class FoodItem(FoodItemBase):
    id: str
    created_at: datetime
    created_by: str
    restaurant_id: Optional[str] = None
    average_rating: Optional[float] = None
    rating_count: int = 0
    is_trending: bool = False
    popularity_score: float = 0.0
    price: Optional[float] = None
    
    class Config:
        orm_mode = True

class RestaurantBase(BaseModel):
    name: str
    description: str
    cuisine_types: List[Cuisine]
    address: str
    city: str
    state: Optional[str] = None
    country: str
    postal_code: str
    phone: str
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    price_range: PriceRange
    opening_hours: Dict[str, str]
    image_url: Optional[str] = None
    social_media: Optional[Dict[str, str]] = None
    features: Optional[List[str]] = None  # e.g., ["Outdoor Seating", "Delivery", "Takeout"]

class RestaurantCreate(RestaurantBase):
    pass

class Restaurant(RestaurantBase):
    id: str
    created_at: datetime
    created_by: str
    average_rating: Optional[float] = None
    rating_count: int = 0
    is_trending: bool = False
    popularity_score: float = 0.0
    
    class Config:
        orm_mode = True

class MenuItem(BaseModel):
    id: str
    restaurant_id: str
    food_item_id: str
    price: float
    available: bool = True
    special: bool = False
    discount_percentage: Optional[float] = None
    
    class Config:
        orm_mode = True

class MenuItemCreate(BaseModel):
    food_item_id: str
    price: float
    available: bool = True
    special: bool = False
    discount_percentage: Optional[float] = None

class MenuSection(BaseModel):
    id: str
    restaurant_id: str
    name: str
    description: Optional[str] = None
    items: List[str]  # List of menu item IDs
    
    class Config:
        orm_mode = True

class MenuSectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    items: List[str] = []

class WishlistItem(BaseModel):
    id: str
    user_id: str
    food_item_id: Optional[str] = None
    restaurant_id: Optional[str] = None
    added_at: datetime
    
    class Config:
        orm_mode = True

class WishlistItemCreate(BaseModel):
    food_item_id: Optional[str] = None
    restaurant_id: Optional[str] = None

class RecommendationRequest(BaseModel):
    cuisine: Optional[Cuisine] = None
    dietary_preferences: Optional[List[DietaryPreference]] = None
    meal_type: Optional[MealType] = None
    max_calories: Optional[int] = None
    max_preparation_time: Optional[int] = None
    time_of_day: Optional[str] = None
    previous_liked: Optional[List[str]] = None
    sort_by: Optional[SortOption] = SortOption.RELEVANCE

class RecommendationResponse(BaseModel):
    recommendations: List[FoodItem]
    count: int

class SearchRequest(BaseModel):
    query: Optional[str] = None
    cuisines: Optional[List[Cuisine]] = None
    dietary_preferences: Optional[List[DietaryPreference]] = None
    meal_types: Optional[List[MealType]] = None
    categories: Optional[List[ItemCategory]] = None
    max_calories: Optional[int] = None
    max_preparation_time: Optional[int] = None
    price_range: Optional[List[PriceRange]] = None
    min_rating: Optional[float] = None
    sort_by: Optional[SortOption] = SortOption.RELEVANCE

class TrendingResponse(BaseModel):
    trending_foods: List[FoodItem]
    trending_restaurants: List[Restaurant]

# Sample data
users_db = {
    "admin": UserInDB(
        id="1",
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=pwd_context.hash("adminpassword"),
        role=UserRole.ADMIN,
        created_at=datetime.now(),
        preferences=UserPreferences(
            language=Language.ENGLISH,
            dark_mode=False,
            dietary_preferences=[],
            favorite_cuisines=[]
        ),
        profile_picture=None
    ),
    "user": UserInDB(
        id="2",
        email="user@example.com",
        username="user",
        full_name="Regular User",
        hashed_password=pwd_context.hash("userpassword"),
        role=UserRole.USER,
        created_at=datetime.now(),
        preferences=UserPreferences(
            language=Language.ENGLISH,
            dark_mode=True,
            dietary_preferences=[DietaryPreference.VEGETARIAN],
            favorite_cuisines=[Cuisine.ITALIAN, Cuisine.INDIAN]
        ),
        profile_picture=None
    )
}

food_items_db = {
    "1": FoodItem(
        id="1",
        name="Amok Trey",
        description="Traditional Cambodian fish curry steamed in banana leaves with coconut milk and kroeung spice paste",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.FOOD,
        dietary_preferences=[DietaryPreference.GLUTEN_FREE],
        meal_types=[MealType.LUNCH, MealType.DINNER],
        calories=380,
        protein=28.0,
        carbs=12.0,
        fat=26.0,
        ingredients=["white fish", "coconut milk", "kroeung paste", "banana leaves", "fish sauce", "palm sugar", "kaffir lime leaves"],
        cook="Traditional steaming method",
        cooking_instructions=[
            "Prepare kroeung paste by grinding lemongrass, galangal, garlic, shallots, and chilies",
            "Mix fish pieces with kroeung paste and marinate for 30 minutes",
            "Combine coconut milk with fish sauce and palm sugar",
            "Line banana leaf cups with the mixture",
            "Steam for 20-25 minutes until set",
            "Garnish with kaffir lime leaves and serve hot"
        ],
        preparation_time_minutes=60,
        image_url="https://chefsclubrecipes.com/wp-content/uploads/2023/07/shutterstock_1189299013-1.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="1",
        average_rating=4.8,
        rating_count=67,
        is_trending=True,
        popularity_score=96.5,
        price=18.99
    ),
    "2": FoodItem(
        id="2",
        name="Lok Lak",
        description="Khmer-style stir-fried beef served with tomatoes, onions, and lime-pepper dipping sauce",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.FOOD,
        dietary_preferences=[DietaryPreference.NONE],
        meal_types=[MealType.LUNCH, MealType.DINNER],
        calories=520,
        protein=35.0,
        carbs=25.0,
        fat=32.0,
        ingredients=["beef sirloin", "tomatoes", "onions", "lettuce", "lime", "black pepper", "soy sauce", "oyster sauce"],
        cook="High-heat stir-frying",
        cooking_instructions=[
            "Cut beef into bite-sized cubes and marinate with soy sauce",
            "Heat wok over high heat with oil",
            "Stir-fry beef until just cooked through",
            "Add onions and tomatoes, stir-fry briefly",
            "Prepare dipping sauce with lime juice, salt, and pepper",
            "Serve over lettuce with jasmine rice and dipping sauce"
        ],
        preparation_time_minutes=25,
        image_url="https://spicygelato.kitchen/wp-content/uploads/2022/03/BeefLokLak-scaled.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="2",
        average_rating=4.7,
        rating_count=54,
        is_trending=True,
        popularity_score=94.0,
        price=16.99
    ),
    "3": FoodItem(
        id="3",
        name="Nom Banh Chok",
        description="Khmer noodles with fish-based green curry sauce, fresh herbs, and vegetables",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.FOOD,
        dietary_preferences=[DietaryPreference.GLUTEN_FREE],
        meal_types=[MealType.BREAKFAST, MealType.LUNCH],
        calories=420,
        protein=22.0,
        carbs=58.0,
        fat=12.0,
        ingredients=["rice noodles", "fish", "lemongrass", "turmeric", "galangal", "cucumber", "bean sprouts", "banana blossom", "mint"],
        cook="Traditional curry preparation",
        cooking_instructions=[
            "Prepare fresh rice noodles by steaming rice flour batter",
            "Make kroeung paste with lemongrass, galangal, and turmeric",
            "Cook fish and blend with kroeung to make curry base",
            "Simmer curry until fragrant and thick",
            "Prepare fresh vegetable accompaniments",
            "Serve noodles topped with curry and fresh herbs"
        ],
        preparation_time_minutes=90,
        image_url="https://grantourismotravels.com/wp-content/uploads/2021/02/Authentic-Nom-Banh-Chok-Recipe-Cambodian-Khmer-Noodles-Copyright-2021-Terence-Carter-Grantourismo.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="3",
        average_rating=4.6,
        rating_count=43,
        is_trending=True,
        popularity_score=92.0,
        price=12.99
    ),
    "4": FoodItem(
        id="4",
        name="Bai Sach Chrouk",
        description="Cambodian broken rice with grilled pork, pickled vegetables, and soup",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.FOOD,
        dietary_preferences=[DietaryPreference.NONE],
        meal_types=[MealType.BREAKFAST, MealType.LUNCH],
        calories=580,
        protein=32.0,
        carbs=65.0,
        fat=22.0,
        ingredients=["broken rice", "pork shoulder", "garlic", "soy sauce", "sugar", "pickled radish", "scallions", "fried shallots"],
        cook="Grilling and rice preparation",
        cooking_instructions=[
            "Marinate pork with garlic, soy sauce, and sugar overnight",
            "Cook broken rice with coconut milk until tender",
            "Grill pork over charcoal until caramelized",
            "Prepare clear soup with scallions",
            "Slice pork and arrange over rice",
            "Serve with pickled vegetables and soup"
        ],
        preparation_time_minutes=40,
        image_url="https://indochinatravel.com/country/cambodia/images/bai-sach-chrouk.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="4",
        average_rating=4.7,
        rating_count=61,
        is_trending=True,
        popularity_score=95.0,
        price=14.99
    ),
    "5": FoodItem(
        id="5",
        name="Kuy Teav",
        description="Cambodian rice noodle soup with pork, shrimp, and fresh herbs",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.FOOD,
        dietary_preferences=[DietaryPreference.NONE],
        meal_types=[MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER],
        calories=450,
        protein=26.0,
        carbs=52.0,
        fat=16.0,
        ingredients=["rice noodles", "pork bones", "ground pork", "shrimp", "fish sauce", "bean sprouts", "cilantro", "lime"],
        cook="Slow-simmered broth preparation",
        cooking_instructions=[
            "Simmer pork bones for 3-4 hours to make clear broth",
            "Prepare rice noodles according to package instructions",
            "Season broth with fish sauce and sugar",
            "Cook ground pork and shrimp separately",
            "Assemble bowl with noodles, meat, and hot broth",
            "Garnish with fresh herbs, bean sprouts, and lime"
        ],
        preparation_time_minutes=45,
        image_url="https://media.urbanistnetwork.com/saigoneer/article-images/2022/12/30/hu-tieu/00b.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="5",
        average_rating=4.8,
        rating_count=72,
        is_trending=True,
        popularity_score=97.0,
        price=11.99
    ),
    "6": FoodItem(
        id="6",
        name="Samlar Kako",
        description="Traditional Cambodian vegetable soup with ground pork and roasted rice powder",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.FOOD,
        dietary_preferences=[DietaryPreference.NONE],
        meal_types=[MealType.LUNCH, MealType.DINNER],
        calories=320,
        protein=18.0,
        carbs=28.0,
        fat=14.0,
        ingredients=["ground pork", "green beans", "eggplant", "roasted rice powder", "tamarind", "fish sauce", "sugar", "herbs"],
        cook="Traditional soup preparation",
        cooking_instructions=[
            "Roast rice until golden and grind into powder",
            "Prepare vegetables by cutting into bite-sized pieces",
            "Cook ground pork with aromatics",
            "Add vegetables and simmer until tender",
            "Season with tamarind, fish sauce, and sugar",
            "Thicken with roasted rice powder and serve hot"
        ],
        preparation_time_minutes=35,
        image_url="https://toursbyjeeps.com/wp-content/uploads/2020/12/Untitled-1.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="6",
        average_rating=4.5,
        rating_count=38,
        is_trending=False,
        popularity_score=88.0,
        price=13.99
    ),
    "7": FoodItem(
        id="7",
        name="Num Pang",
        description="Cambodian baguette sandwich with pâté, pickled vegetables, and herbs",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.FOOD,
        dietary_preferences=[DietaryPreference.NONE],
        meal_types=[MealType.BREAKFAST, MealType.LUNCH, MealType.SNACK],
        calories=480,
        protein=20.0,
        carbs=55.0,
        fat=20.0,
        ingredients=["French baguette", "pork pate", "pickled daikon", "pickled carrot", "cucumber", "cilantro", "mayonnaise", "soy sauce"],
        cook="Assembly sandwich preparation",
        cooking_instructions=[
            "Slice baguette lengthwise and hollow out some bread",
            "Spread pâté and mayonnaise on both sides",
            "Layer with pickled vegetables and cucumber",
            "Add fresh cilantro and a dash of soy sauce",
            "Press sandwich lightly and slice in half",
            "Serve immediately while bread is crispy"
        ],
        preparation_time_minutes=10,
        image_url="https://pyxis.nymag.com/v1/imgs/9c6/6e9/0ba4fff1b43fb2fa234bea8f9dd1cc9d7b-num-pang-01.rsocial.w1200.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="7",
        average_rating=4.6,
        rating_count=49,
        is_trending=True,
        popularity_score=91.0,
        price=8.99
    ),
    "8": FoodItem(
        id="8",
        name="Pleah Sach Ko",
        description="Cambodian beef salad with lime dressing, herbs, and roasted rice powder",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.FOOD,
        dietary_preferences=[DietaryPreference.GLUTEN_FREE],
        meal_types=[MealType.LUNCH, MealType.DINNER],
        calories=380,
        protein=28.0,
        carbs=15.0,
        fat=24.0,
        ingredients=["beef", "lime juice", "fish sauce", "mint", "cilantro", "roasted rice powder", "chilies", "shallots"],
        cook="Raw preparation salad",
        cooking_instructions=[
            "Slice beef very thinly and blanch briefly in boiling water",
            "Prepare dressing with lime juice, fish sauce, and sugar",
            "Roast rice until golden and grind coarsely",
            "Toss beef with dressing and let marinate",
            "Add fresh herbs, chilies, and shallots",
            "Sprinkle with roasted rice powder before serving"
        ],
        preparation_time_minutes=20,
        image_url="https://i.pinimg.com/originals/7d/bb/34/7dbb3495705f3dbae16bb6663b5cd3af.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="8",
        average_rating=4.4,
        rating_count=35,
        is_trending=False,
        popularity_score=86.0,
        price=15.99
    ),
    "9": FoodItem(
        id="9",
        name="Kralan",
        description="Traditional Cambodian sticky rice cake cooked in bamboo with coconut milk and black beans",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.DESSERT,
        dietary_preferences=[DietaryPreference.VEGETARIAN, DietaryPreference.VEGAN, DietaryPreference.GLUTEN_FREE],
        meal_types=[MealType.SNACK, MealType.DESSERT],
        calories=280,
        protein=4.0,
        carbs=58.0,
        fat=6.0,
        ingredients=["glutinous rice", "coconut milk", "black beans", "palm sugar", "salt", "banana leaves", "bamboo tubes"],
        cook="Traditional bamboo cooking",
        cooking_instructions=[
            "Soak glutinous rice and black beans overnight",
            "Mix rice with coconut milk, palm sugar, and salt",
            "Line bamboo tubes with banana leaves",
            "Fill tubes with rice mixture and seal",
            "Cook over charcoal fire for 2-3 hours",
            "Cool before removing from bamboo and slicing"
        ],
        preparation_time_minutes=180,
        image_url="https://www.neverendingvoyage.com/wp-content/uploads/2014/04/kralan-cambodia-2-1100x825.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="9",
        average_rating=4.7,
        rating_count=41,
        is_trending=True,
        popularity_score=93.0,
        price=6.99
    ),
    "10": FoodItem(
        id="10",
        name="Tuk Krolok",
        description="Sweet Cambodian drink made with coconut milk, tapioca pearls, and palm sugar",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.DRINK,
        drink_type=DrinkType.SMOOTHIE,
        dietary_preferences=[DietaryPreference.VEGETARIAN, DietaryPreference.VEGAN, DietaryPreference.GLUTEN_FREE],
        meal_types=[MealType.SNACK, MealType.DESSERT],
        calories=220,
        protein=2.0,
        carbs=45.0,
        fat=8.0,
        ingredients=["coconut milk", "tapioca pearls", "palm sugar", "pandan leaves", "ice", "salt"],
        cook="Traditional drink preparation",
        cooking_instructions=[
            "Cook tapioca pearls until translucent",
            "Prepare coconut milk with palm sugar and salt",
            "Add pandan leaves for flavor and color",
            "Combine cooked pearls with sweetened coconut milk",
            "Chill thoroughly before serving",
            "Serve over ice with additional coconut milk"
        ],
        preparation_time_minutes=30,
        image_url="https://images.deliveryhero.io/image/fd-kh/products/964854.jpg?width=%s",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="10",
        average_rating=4.6,
        rating_count=28,
        is_trending=True,
        popularity_score=89.0,
        price=5.99
    ),
    "11": FoodItem(
        id="11",
        name="Samlor Kari",
        description="Cambodian chicken curry with sweet potatoes, green beans, and coconut milk",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.FOOD,
        dietary_preferences=[DietaryPreference.GLUTEN_FREE],
        meal_types=[MealType.LUNCH, MealType.DINNER],
        calories=520,
        protein=30.0,
        carbs=35.0,
        fat=28.0,
        ingredients=["chicken", "coconut milk", "curry paste", "sweet potatoes", "green beans", "fish sauce", "palm sugar", "thai basil"],
        cook="Traditional curry cooking",
        cooking_instructions=[
            "Prepare kroeung curry paste with spices and herbs",
            "Brown chicken pieces in a pot",
            "Add curry paste and cook until fragrant",
            "Pour in coconut milk and bring to boil",
            "Add vegetables and simmer until tender",
            "Season with fish sauce and palm sugar, garnish with basil"
        ],
        preparation_time_minutes=45,
        image_url="https://media2.fishtank.my/media/syokenglish/assets/policies/screenshot-2025-05-14-at-14-22-03.png",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="11",
        average_rating=4.8,
        rating_count=56,
        is_trending=True,
        popularity_score=95.5,
        price=17.99
    ),
    "12": FoodItem(
        id="12",
        name="Cha Houy Teuk",
        description="Cambodian jelly drink with grass jelly, coconut milk, and palm sugar syrup",
        cuisine=Cuisine.CAMBODIAN,
        category=ItemCategory.DRINK,
        drink_type=DrinkType.SMOOTHIE,
        dietary_preferences=[DietaryPreference.VEGETARIAN, DietaryPreference.VEGAN, DietaryPreference.GLUTEN_FREE],
        meal_types=[MealType.SNACK, MealType.DESSERT],
        calories=180,
        protein=1.0,
        carbs=38.0,
        fat=5.0,
        ingredients=["grass jelly", "coconut milk", "palm sugar", "ice", "pandan leaves"],
        cook="Cold beverage preparation",
        cooking_instructions=[
            "Prepare grass jelly according to package instructions",
            "Make palm sugar syrup with pandan leaves",
            "Cut jelly into small cubes",
            "Layer jelly in glasses with syrup",
            "Top with coconut milk and ice",
            "Stir before drinking and serve immediately"
        ],
        preparation_time_minutes=15,
        image_url="https://holidaytoindochina.com/webroot/img/images/post_categories/Cha-houy-teuk.jpg",
        created_at=datetime.now(),
        created_by="1",
        restaurant_id="12",
        average_rating=4.5,
        rating_count=33,
        is_trending=False,
        popularity_score=87.5,
        price=4.99
    )
}

menu_items_db = {
    "1": MenuItem(
        id="1",
        restaurant_id="1",
        food_item_id="1",
        price=15.99,
        available=True,
        special=False
    ),
    "2": MenuItem(
        id="2",
        restaurant_id="2",
        food_item_id="2",
        price=12.99,
        available=True,
        special=True
    ),
    "3": MenuItem(
        id="3",
        restaurant_id="3",
        food_item_id="3",
        price=8.99,
        available=True,
        special=False
    ),
    "4": MenuItem(
        id="4",
        restaurant_id="4",
        food_item_id="4",
        price=10.99,
        available=True,
        special=False
    ),
    "5": MenuItem(
        id="5",
        restaurant_id="5",
        food_item_id="5",
        price=3.99,
        available=True,
        special=False
    ),
    "6": MenuItem(
        id="6",
        restaurant_id="6",
        food_item_id="6",
        price=18.99,
        available=True,
        special=True
    ),
    "7": MenuItem(
        id="7",
        restaurant_id="7",
        food_item_id="7",
        price=9.99,
        available=True,
        special=False
    ),
    "8": MenuItem(
        id="8",
        restaurant_id="8",
        food_item_id="8",
        price=14.99,
        available=True,
        special=False
    ),
    "9": MenuItem(
        id="9",
        restaurant_id="9",
        food_item_id="9",
        price=11.99,
        available=True,
        special=True
    ),
    "10": MenuItem(
        id="10",
        restaurant_id="10",
        food_item_id="10",
        price=13.99,
        available=True,
        special=False
    ),
    "11": MenuItem(
        id="11",
        restaurant_id="3",
        food_item_id="11",
        price=4.99,
        available=True,
        special=False
    ),
    "12": MenuItem(
        id="12",
        restaurant_id="9",
        food_item_id="12",
        price=6.99,
        available=True,
        special=True
    ),
    "13": MenuItem(
        id="13",
        restaurant_id="4",
        food_item_id="13",
        price=9.99,
        available=True,
        special=False
    ),
    "14": MenuItem(
        id="14",
        restaurant_id="6",
        food_item_id="14",
        price=3.99,
        available=True,
        special=False
    ),
    "15": MenuItem(
        id="15",
        restaurant_id="1",
        food_item_id="15",
        price=5.99,
        available=True,
        special=False
    ),
}

menu_sections_db = {
    "1": MenuSection(
        id="1",
        restaurant_id="1",
        name="Pasta",
        description="Our signature pasta dishes",
        items=["1", "15"]
    ),
    "2": MenuSection(
        id="2",
        restaurant_id="2",
        name="Curries",
        description="Traditional Indian curries",
        items=["2"]
    ),
    "3": MenuSection(
        id="3",
        restaurant_id="3",
        name="Breakfast",
        description="Morning favorites",
        items=["3"]
    ),
    "4": MenuSection(
        id="4",
        restaurant_id="3",
        name="Drinks",
        description="Hot and cold beverages",
        items=["11"]
    ),
    "5": MenuSection(
        id="5",
        restaurant_id="4",
        name="Tacos",
        description="Authentic Mexican tacos",
        items=["4"]
    ),
    "6": MenuSection(
        id="6",
        restaurant_id="4",
        name="Drinks",
        description="Refreshing beverages",
        items=["13"]
    ),
    "7": MenuSection(
        id="7",
        restaurant_id="5",
        name="Desserts",
        description="Sweet treats",
        items=["5"]
    ),
    "8": MenuSection(
        id="8",
        restaurant_id="6",
        name="Sushi",
        description="Fresh sushi rolls",
        items=["6"]
    ),
    "9": MenuSection(
        id="9",
        restaurant_id="6",
        name="Drinks",
        description="Traditional Japanese beverages",
        items=["14"]
    ),
    "10": MenuSection(
        id="10",
        restaurant_id="7",
        name="Salads",
        description="Fresh Mediterranean salads",
        items=["7"]
    ),
    "11": MenuSection(
        id="11",
        restaurant_id="8",
        name="Stir Fry",
        description="Wok-fried specialties",
        items=["8"]
    ),
    "12": MenuSection(
        id="12",
        restaurant_id="9",
        name="Breakfast",
        description="Plant-based breakfast options",
        items=["9"]
    ),
    "13": MenuSection(
        id="13",
        restaurant_id="9",
        name="Drinks",
        description="Refreshing smoothies and juices",
        items=["12"]
    ),
    "14": MenuSection(
        id="14",
        restaurant_id="10",
        name="Noodles",
        description="Traditional Thai noodle dishes",
        items=["10"]
    ),
}

wishlist_db = {
    "1": WishlistItem(
        id="1",
        user_id="2",
        food_item_id="1",
        restaurant_id=None,
        added_at=datetime.now()
    ),
    "2": WishlistItem(
        id="2",
        user_id="2",
        food_item_id=None,
        restaurant_id="6",
        added_at=datetime.now()
    ),
    "3": WishlistItem(
        id="3",
        user_id="2",
        food_item_id="12",
        restaurant_id=None,
        added_at=datetime.now()
    ),
}

ratings_db = {
    "1": Rating(
        id="1",
        user_id="2",
        food_item_id="1",
        restaurant_id=None,
        rating=5.0,
        review="Absolutely delicious! Best carbonara I've ever had.",
        created_at=datetime.now() - timedelta(days=10),
        updated_at=None
    ),
    "2": Rating(
        id="2",
        user_id="2",
        food_item_id=None,
        restaurant_id="6",
        rating=4.5,
        review="Great atmosphere and excellent service. The sushi was very fresh.",
        created_at=datetime.now() - timedelta(days=5),
        updated_at=None
    ),
    "3": Rating(
        id="3",
        user_id="1",
        food_item_id="4",
        restaurant_id=None,
        rating=4.0,
        review="The tacos were tasty but could use a bit more spice.",
        created_at=datetime.now() - timedelta(days=15),
        updated_at=None
    ),
    "4": Rating(
        id="4",
        user_id="1",
        food_item_id=None,
        restaurant_id="3",
        rating=5.0,
        review="Best breakfast place in town! Love their avocado toast.",
        created_at=datetime.now() - timedelta(days=20),
        updated_at=None
    ),
}

# Add these sample databases after the existing sample databases
review_votes_db = {}
review_reports_db = {}
review_responses_db = {}

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user_by_email(email: str):
    for user in users_db.values():
        if user.email == email:
            return user
    return None

def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         email: str = payload.get("sub")
#         if email is None:
#             raise credentials_exception
#         token_data = TokenData(username=email)
#     except jwt.PyJWTError:
#         raise credentials_exception
#     user = get_user_by_email(email=token_data.username)
#     if user is None:
#         raise credentials_exception
#     return user

# async def get_current_active_user(current_user: User = Depends(get_current_user)):
#     return current_user

# async def get_admin_user(current_user: User = Depends(get_current_active_user)):
#     if current_user.role != UserRole.ADMIN:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not enough permissions"
#         )
#     return current_user

# Helper functions
def calculate_average_rating(ratings):
    if not ratings:
        return None
    return sum(r.rating for r in ratings) / len(ratings)

def update_trending_status():
    """Update trending status for food items and restaurants based on recent ratings and views"""
    # This would typically be a scheduled task
    # For simplicity, we're just setting some items as trending
    pass

# API endpoints
@app.post("/login", response_model=Token, tags=["Authentication"])
async def login_for_access_token(email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.post("/register", response_model=User, tags=["Authentication"])
async def register_user(user: UserCreate):
    # Check if the username or email is already registered
    if user.username in users_db or any(u.email == user.email for u in users_db.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user.password)
    
    # Create the new user
    db_user = UserInDB(
        id=user_id,
        email=user.email,
        username=user.username,
        full_name=None,  # Optional field
        hashed_password=hashed_password,
        role=UserRole.USER,  # Default role is USER
        created_at=datetime.now(),
        preferences=UserPreferences(),  # Default preferences
        profile_picture=None  # Optional field
    )
    
    users_db[user.username] = db_user
    
    return db_user

# @app.get("/users/me", response_model=User, tags=["Users"])
# async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# @app.put("/users/me", response_model=User, tags=["Users"])
# async def update_user(
#     user_update: UserUpdate,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Update current user's information"""
#     user = users_db[current_user.username]
    
#     if user_update.email:
#         user.email = user_update.email
    
#     if user_update.full_name:
#         user.full_name = user_update.full_name
    
#     if user_update.profile_picture:
#         user.profile_picture = user_update.profile_picture
    
#     if user_update.preferences:
#         # Update only the provided preference fields
#         if user_update.preferences.language:
#             user.preferences.language = user_update.preferences.language
        
#         if user_update.preferences.dark_mode is not None:
#             user.preferences.dark_mode = user_update.preferences.dark_mode
        
#         if user_update.preferences.dietary_preferences:
#             user.preferences.dietary_preferences = user_update.preferences.dietary_preferences
        
#         if user_update.preferences.favorite_cuisines:
#             user.preferences.favorite_cuisines = user_update.preferences.favorite_cuisines
        
#         if user_update.preferences.price_range_preference:
#             user.preferences.price_range_preference = user_update.preferences.price_range_preference
    
#     users_db[current_user.username] = user
#     return user

# @app.post("/users/", response_model=User, tags=["Users"])
# async def create_user(user: UserCreate):
#     """Create a new user (admin only)"""
#     if user.username in users_db:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Username already registered"
#         )
    
#     user_id = str(uuid.uuid4())
#     hashed_password = get_password_hash(user.password)
    
#     # Set default preferences if not provided
#     if not user.preferences:
#         user.preferences = UserPreferences()
    
#     db_user = UserInDB(
#         id=user_id,
#         email=user.email,
#         username=user.username,
#         full_name=user.full_name,
#         hashed_password=hashed_password,
#         role=UserRole.USER,  # Default role is USER
#         created_at=datetime.now(),
#         preferences=user.preferences,
#         profile_picture=user.profile_picture
#     )
    
#     users_db[user.username] = db_user
    
#     return db_user

# @app.get("/users/", response_model=List[User], tags=["Users"])
# async def read_users(current_user: User = Depends(get_admin_user)):
#     """Get all users (admin only)"""
#     return list(users_db.values())

# Root endpoint
@app.get("/api/v1/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Food Recommendation API"}

# Reference data endpoints
@app.get("/cuisines", tags=["Reference Data"])
async def get_cuisines():
    """Get all available cuisine types"""
    return [cuisine.value for cuisine in Cuisine]

@app.get("/dietary-preferences", tags=["Reference Data"])
async def get_dietary_preferences():
    """Get all available dietary preferences"""
    return [pref.value for pref in DietaryPreference]

@app.get("/meal-types", tags=["Reference Data"])
async def get_meal_types():
    """Get all available meal types"""
    return [meal.value for meal in MealType]

@app.get("/price-ranges", tags=["Reference Data"])
async def get_price_ranges():
    """Get all available price ranges"""
    return [price.value for price in PriceRange]

@app.get("/item-categories", tags=["Reference Data"])
async def get_item_categories():
    """Get all available item categories"""
    return [category.value for category in ItemCategory]

@app.get("/drink-types", tags=["Reference Data"])
async def get_drink_types():
    """Get all available drink types"""
    return [drink_type.value for drink_type in DrinkType]

@app.get("/languages", tags=["Reference Data"])
async def get_languages():
    """Get all available languages"""
    return [language.value for language in Language]

# Food item endpoints
@app.get("/food-items", response_model=List[FoodItem], tags=["Food Items"])
async def get_food_items(
    cuisine: Optional[Cuisine] = None,
    dietary_preference: Optional[List[DietaryPreference]] = Query(None),
    meal_type: Optional[MealType] = None,
    category: Optional[ItemCategory] = None,
    drink_type: Optional[DrinkType] = None,
    max_calories: Optional[int] = None,
    max_preparation_time: Optional[int] = None,
    min_rating: Optional[float] = None,
    is_trending: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: Optional[SortOption] = SortOption.RELEVANCE
):
    """Get all food items with optional filtering"""
    filtered_items = list(food_items_db.values())
    
    if cuisine:
        filtered_items = [item for item in filtered_items if item.cuisine == cuisine]
    
    if dietary_preference:
        filtered_items = [
            item for item in filtered_items 
            if all(pref in item.dietary_preferences for pref in dietary_preference)
        ]
    
    if meal_type:
        filtered_items = [item for item in filtered_items if meal_type in item.meal_types]
    
    if category:
        filtered_items = [item for item in filtered_items if item.category == category]
    
    if drink_type:
        filtered_items = [item for item in filtered_items if item.drink_type == drink_type]
    
    if max_calories:
        filtered_items = [item for item in filtered_items if item.calories and item.calories <= max_calories]
    
    if max_preparation_time:
        filtered_items = [item for item in filtered_items if item.preparation_time_minutes and item.preparation_time_minutes <= max_preparation_time]
    
    if min_rating:
        filtered_items = [item for item in filtered_items if item.average_rating and item.average_rating >= min_rating]
    
    if is_trending is not None:
        filtered_items = [item for item in filtered_items if item.is_trending == is_trending]
    
    if search:
        search = search.lower()
        filtered_items = [
            item for item in filtered_items 
            if search in item.name.lower() or search in item.description.lower() or 
            any(search in ingredient.lower() for ingredient in item.ingredients)
        ]
    
    if search:
        search = search.lower()
        filtered_items = [
            item for item in filtered_items 
            if search in item.name.lower() or search in item.description.lower() or 
            any(search in ingredient.lower() for ingredient in item.ingredients)
        ]
        filtered_items = [
            item for item in filtered_items

            if search in item.name.lower() or search in item.description.lower() or
            any(search in ingredient.lower() for ingredient in item.ingredients)
        ]
    
    # Sort items based on sort_by parameter
    if sort_by == SortOption.RATING:
        filtered_items.sort(key=lambda x: x.average_rating if x.average_rating else 0, reverse=True)
    elif sort_by == SortOption.TRENDING:
        filtered_items.sort(key=lambda x: (x.is_trending, x.popularity_score), reverse=True)
    elif sort_by == SortOption.PRICE_LOW:
        filtered_items.sort(key=lambda x: x.price if x.price else float('inf'))
    elif sort_by == SortOption.PRICE_HIGH:
        filtered_items.sort(key=lambda x: x.price if x.price else 0, reverse=True)
    elif sort_by == SortOption.NEWEST:
        filtered_items.sort(key=lambda x: x.created_at, reverse=True)
    
    return filtered_items

@app.get("/food-items/{food_id}", response_model=FoodItem, tags=["Food Items"])
async def get_food_item(food_id: str):
    """Get a specific food item by ID"""
    if food_id not in food_items_db:
        raise HTTPException(status_code=404, detail="Food item not found")
    return food_items_db[food_id]

@app.post("/food-items", response_model=FoodItem, status_code=status.HTTP_201_CREATED, tags=["Food Items"])
async def create_food_item(food_item: FoodItemCreate):
    """Create a new food item"""
    food_id = str(uuid.uuid4())
    
    db_food_item = FoodItem(
        id=food_id,
        **food_item.dict(),
        created_at=datetime.now(),
        restaurant_id=None,
        average_rating=None,
        rating_count=0,
        is_trending=False,
        popularity_score=0.0,
        price=None
    )
    
    food_items_db[food_id] = db_food_item
    return db_food_item

@app.put("/food-items/{food_id}", response_model=FoodItem, tags=["Food Items"])
async def update_food_item(
    food_id: str, 
    food_item: FoodItemCreate
):
    """Update a food item"""
    if food_id not in food_items_db:
        raise HTTPException(status_code=404, detail="Food item not found")
    
    # Update the food item
    db_food_item = food_items_db[food_id]
    update_data = food_item.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_food_item, key, value)
    
    food_items_db[food_id] = db_food_item
    return db_food_item

@app.delete("/food-items/{food_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Food Items"])
async def delete_food_item(food_id: str):
    """Delete a food item (admin only)"""
    if food_id not in food_items_db:
        raise HTTPException(status_code=404, detail="Food item not found")
    
    del food_items_db[food_id]
    return None

# # Restaurant endpoints
# @app.get("/restaurants", response_model=List[Restaurant], tags=["Restaurants"])
# async def get_restaurants(
#     cuisine: Optional[List[Cuisine]] = Query(None),
#     price_range: Optional[List[PriceRange]] = Query(None),
#     min_rating: Optional[float] = None,
#     is_trending: Optional[bool] = None,
#     features: Optional[List[str]] = Query(None),
#     search: Optional[str] = None,
#     sort_by: Optional[SortOption] = SortOption.RELEVANCE,
# ):
#     """Get all restaurants with optional filtering"""
#     filtered_restaurants = list(restaurants_db.values())
    
#     if cuisine:
#         filtered_restaurants = [
#             restaurant for restaurant in filtered_restaurants 
#             if any(c in restaurant.cuisine_types for c in cuisine)
#         ]
    
#     if price_range:
#         filtered_restaurants = [
#             restaurant for restaurant in filtered_restaurants 
#             if restaurant.price_range in price_range
#         ]
    
#     if min_rating:
#         filtered_restaurants = [
#             restaurant for restaurant in filtered_restaurants 
#             if restaurant.average_rating and restaurant.average_rating >= min_rating
#         ]
    
#     if is_trending is not None:
#         filtered_restaurants = [
#             restaurant for restaurant in filtered_restaurants 
#             if restaurant.is_trending == is_trending
#         ]
    
#     if features:
#         filtered_restaurants = [
#             restaurant for restaurant in filtered_restaurants 
#             if restaurant.features and all(feature in restaurant.features for feature in features)
#         ]
    
#     if search:
#         search = search.lower()
#         filtered_restaurants = [
#             restaurant for restaurant in filtered_restaurants 
#             if search in restaurant.name.lower() or search in restaurant.description.lower() or
#             search in restaurant.city.lower() or search in restaurant.address.lower()
#         ]
    
#     # Sort restaurants based on sort_by parameter
#     if sort_by == SortOption.RATING:
#         filtered_restaurants.sort(key=lambda x: x.average_rating if x.average_rating else 0, reverse=True)
#     elif sort_by == SortOption.TRENDING:
#         filtered_restaurants.sort(key=lambda x: (x.is_trending, x.popularity_score), reverse=True)
#     elif sort_by == SortOption.PRICE_LOW:
#         filtered_restaurants.sort(key=lambda x: {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4}[x.price_range])
#     elif sort_by == SortOption.PRICE_HIGH:
#         filtered_restaurants.sort(key=lambda x: {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4}[x.price_range], reverse=True)
#     elif sort_by == SortOption.NEWEST:
#         filtered_restaurants.sort(key=lambda x: x.created_at, reverse=True)
    
#     return filtered_restaurants

# @app.get("/restaurants/{restaurant_id}", response_model=Restaurant, tags=["Restaurants"])
# async def get_restaurant(restaurant_id: str):
#     """Get a specific restaurant by ID"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
#     return restaurants_db[restaurant_id]

# @app.post("/restaurants", response_model=Restaurant, status_code=status.HTTP_201_CREATED, tags=["Restaurants"])
# async def create_restaurant(restaurant: RestaurantCreate):
#     """Create a new restaurant (admin only)"""
#     restaurant_id = str(uuid.uuid4())
    
#     db_restaurant = Restaurant(
#         id=restaurant_id,
#         **restaurant.dict(),
#         created_at=datetime.now(),
        
#         average_rating=None,
#         rating_count=0,
#         is_trending=False,
#         popularity_score=0.0
#     )
    
#     restaurants_db[restaurant_id] = db_restaurant
#     return db_restaurant

# @app.put("/restaurants/{restaurant_id}", response_model=Restaurant, tags=["Restaurants"])
# async def update_restaurant(
#     restaurant_id: str, 
#     restaurant: RestaurantCreate, 
#     current_user: User = Depends(get_admin_user)
# ):
#     """Update a restaurant (admin only)"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     # Update the restaurant
#     db_restaurant = restaurants_db[restaurant_id]
#     update_data = restaurant.dict(exclude_unset=True)
    
#     for key, value in update_data.items():
#         setattr(db_restaurant, key, value)
    
#     restaurants_db[restaurant_id] = db_restaurant
#     return db_restaurant

# @app.delete("/restaurants/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Restaurants"])
# async def delete_restaurant(restaurant_id: str):
#     """Delete a restaurant (admin only)"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     del restaurants_db[restaurant_id]
#     return None

# # Menu item endpoints
# @app.get("/restaurants/{restaurant_id}/menu", response_model=List[Dict[str, Any]], tags=["Menu Items"])
# async def get_restaurant_menu(restaurant_id: str, current_user: User = Depends(get_current_active_user)):
#     """Get the menu for a specific restaurant with sections and items"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     # Get all menu sections for this restaurant
#     sections = [section for section in menu_sections_db.values() if section.restaurant_id == restaurant_id]
    
#     # Build the menu with sections and items
#     menu = []
#     for section in sections:
#         section_data = {
#             "id": section.id,
#             "name": section.name,
#             "description": section.description,
#             "items": []
#         }
        
#         # Add items to the section
#         for item_id in section.items:
#             if item_id in menu_items_db:
#                 menu_item = menu_items_db[item_id]
#                 food_item = food_items_db.get(menu_item.food_item_id)
                
#                 if food_item:
#                     item_data = {
#                         "id": menu_item.id,
#                         "food_item_id": food_item.id,
#                         "name": food_item.name,
#                         "description": food_item.description,
#                         "price": menu_item.price,
#                         "available": menu_item.available,
#                         "special": menu_item.special,
#                         "discount_percentage": menu_item.discount_percentage,
#                         "category": food_item.category,
#                         "image_url": food_item.image_url,
#                         "average_rating": food_item.average_rating,
#                         "rating_count": food_item.rating_count
#                     }
#                     section_data["items"].append(item_data)
        
#         menu.append(section_data)
    
#     return menu

# @app.post("/restaurants/{restaurant_id}/menu-sections", response_model=MenuSection, status_code=status.HTTP_201_CREATED, tags=["Menu Items"])
# async def add_menu_section(
#     restaurant_id: str, 
#     menu_section: MenuSectionCreate, 
#     current_user: User = Depends(get_admin_user)
# ):
#     """Add a menu section to a restaurant (admin only)"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     # Validate that all items exist
#     for item_id in menu_section.items:
#         if item_id not in menu_items_db:
#             raise HTTPException(status_code=404, detail=f"Menu item {item_id} not found")
        
#         # Check that the item belongs to this restaurant
#         if menu_items_db[item_id].restaurant_id != restaurant_id:
#             raise HTTPException(status_code=400, detail=f"Menu item {item_id} does not belong to this restaurant")
    
#     section_id = str(uuid.uuid4())
    
#     db_menu_section = MenuSection(
#         id=section_id,
#         restaurant_id=restaurant_id,
#         **menu_section.dict()
#     )
    
#     menu_sections_db[section_id] = db_menu_section
#     return db_menu_section

# @app.post("/restaurants/{restaurant_id}/menu", response_model=MenuItem, status_code=status.HTTP_201_CREATED, tags=["Menu Items"])
# async def add_menu_item(
#     restaurant_id: str, 
#     menu_item: MenuItemCreate, 
#     current_user: User = Depends(get_admin_user)
# ):
#     """Add a menu item to a restaurant (admin only)"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     if menu_item.food_item_id not in food_items_db:
#         raise HTTPException(status_code=404, detail="Food item not found")
    
#     menu_item_id = str(uuid.uuid4())
    
#     db_menu_item = MenuItem(
#         id=menu_item_id,
#         restaurant_id=restaurant_id,
#         **menu_item.dict()
#     )
    
#     menu_items_db[menu_item_id] = db_menu_item
    
#     # Update the food item with the restaurant ID
#     food_item = food_items_db[menu_item.food_item_id]
#     food_item.restaurant_id = restaurant_id
#     food_item.price = menu_item.price
#     food_items_db[menu_item.food_item_id] = food_item
    
#     return db_menu_item

# @app.delete("/menu-items/{menu_item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Menu Items"])
# async def delete_menu_item(menu_item_id: str, current_user: User = Depends(get_admin_user)):
#     """Delete a menu item (admin only)"""
#     if menu_item_id not in menu_items_db:
#         raise HTTPException(status_code=404, detail="Menu item not found")
    
#     # Remove the menu item from any sections it's in
#     for section in menu_sections_db.values():
#         if menu_item_id in section.items:
#             section.items.remove(menu_item_id)
    
#     del menu_items_db[menu_item_id]
#     return None

# # Rating endpoints
# @app.post("/ratings", response_model=Rating, status_code=status.HTTP_201_CREATED, tags=["Ratings"])
# async def create_rating(rating: RatingCreate, current_user: User = Depends(get_current_active_user)):
#     """Create a new rating for a food item or restaurant"""
#     # Validate that at least one of food_item_id or restaurant_id is provided
#     if not rating.food_item_id and not rating.restaurant_id:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Either food_item_id or restaurant_id must be provided"
#         )
    
#     # Validate that the food item or restaurant exists
#     if rating.food_item_id and rating.food_item_id not in food_items_db:
#         raise HTTPException(status_code=404, detail="Food item not found")
    
#     if rating.restaurant_id and rating.restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     # Check if the user has already rated this item
#     for existing_rating in ratings_db.values():
#         if existing_rating.user_id == current_user.id:
#             if (rating.food_item_id and existing_rating.food_item_id == rating.food_item_id) or \
#                (rating.restaurant_id and existing_rating.restaurant_id == rating.restaurant_id):
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="You have already rated this item"
#                 )
    
#     rating_id = str(uuid.uuid4())
    
#     db_rating = Rating(
#         id=rating_id,
#         user_id=current_user.id,
#         **rating.dict(),
#         created_at=datetime.now(),
#         updated_at=None
#     )
    
#     ratings_db[rating_id] = db_rating
    
#     # Update the average rating for the food item or restaurant
#     if rating.food_item_id:
#         food_item = food_items_db[rating.food_item_id]
#         food_item_ratings = [r for r in ratings_db.values() if r.food_item_id == rating.food_item_id]
#         food_item.average_rating = calculate_average_rating(food_item_ratings)
#         food_item.rating_count = len(food_item_ratings)
#         food_items_db[rating.food_item_id] = food_item
    
#     if rating.restaurant_id:
#         restaurant = restaurants_db[rating.restaurant_id]
#         restaurant_ratings = [r for r in ratings_db.values() if r.restaurant_id == rating.restaurant_id]
#         restaurant.average_rating = calculate_average_rating(restaurant_ratings)
#         restaurant.rating_count = len(restaurant_ratings)
#         restaurants_db[rating.restaurant_id] = restaurant
    
#     return db_rating

# @app.get("/ratings/me", response_model=List[Rating], tags=["Ratings"])
# async def get_my_ratings(current_user: User = Depends(get_current_active_user)):
#     """Get all ratings by the current user"""
#     user_ratings = [rating for rating in ratings_db.values() if rating.user_id == current_user.id]
#     return user_ratings

# @app.get("/food-items/{food_id}/ratings", response_model=List[Rating], tags=["Ratings"])
# async def get_food_item_ratings(food_id: str, current_user: User = Depends(get_current_active_user)):
#     """Get all ratings for a specific food item"""
#     if food_id not in food_items_db:
#         raise HTTPException(status_code=404, detail="Food item not found")
    
#     food_ratings = [rating for rating in ratings_db.values() if rating.food_item_id == food_id]
#     return food_ratings

# @app.get("/restaurants/{restaurant_id}/ratings", response_model=List[Rating], tags=["Ratings"])
# async def get_restaurant_ratings(restaurant_id: str, current_user: User = Depends(get_current_active_user)):
#     """Get all ratings for a specific restaurant"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     restaurant_ratings = [rating for rating in ratings_db.values() if rating.restaurant_id == restaurant_id]
#     return restaurant_ratings

# @app.put("/ratings/{rating_id}", response_model=Rating, tags=["Ratings"])
# async def update_rating(
#     rating_id: str, 
#     rating_update: RatingUpdate, 
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Update a rating"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     # Check if the rating belongs to the current user
#     if ratings_db[rating_id].user_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Not enough permissions")
    
#     # Update the rating
#     db_rating = ratings_db[rating_id]
    
#     if rating_update.rating is not None:
#         db_rating.rating = rating_update.rating
    
#     if rating_update.review is not None:
#         db_rating.review = rating_update.review
    
#     db_rating.updated_at = datetime.now()
#     ratings_db[rating_id] = db_rating
    
#     # Update the average rating for the food item or restaurant
#     if db_rating.food_item_id:
#         food_item = food_items_db[db_rating.food_item_id]
#         food_item_ratings = [r for r in ratings_db.values() if r.food_item_id == db_rating.food_item_id]
#         food_item.average_rating = calculate_average_rating(food_item_ratings)
#         food_items_db[db_rating.food_item_id] = food_item
    
#     if db_rating.restaurant_id:
#         restaurant = restaurants_db[db_rating.restaurant_id]
#         restaurant_ratings = [r for r in ratings_db.values() if r.restaurant_id == db_rating.restaurant_id]
#         restaurant.average_rating = calculate_average_rating(restaurant_ratings)
#         restaurants_db[db_rating.restaurant_id] = restaurant
    
#     return db_rating

# @app.delete("/ratings/{rating_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Ratings"])
# async def delete_rating(rating_id: str, current_user: User = Depends(get_current_active_user)):
#     """Delete a rating"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     # Check if the rating belongs to the current user or if the user is an admin
#     if ratings_db[rating_id].user_id != current_user.id and current_user.role != UserRole.ADMIN:
#         raise HTTPException(status_code=403, detail="Not enough permissions")
    
#     # Store the food_item_id and restaurant_id before deleting
#     food_item_id = ratings_db[rating_id].food_item_id
#     restaurant_id = ratings_db[rating_id].restaurant_id
    
#     del ratings_db[rating_id]
    
#     # Update the average rating for the food item or restaurant
#     if food_item_id:
#         food_item = food_items_db[food_item_id]
#         food_item_ratings = [r for r in ratings_db.values() if r.food_item_id == food_item_id]
#         food_item.average_rating = calculate_average_rating(food_item_ratings)
#         food_item.rating_count = len(food_item_ratings)
#         food_items_db[food_item_id] = food_item
    
#     if restaurant_id:
#         restaurant = restaurants_db[restaurant_id]
#         restaurant_ratings = [r for r in ratings_db.values() if r.restaurant_id == restaurant_id]
#         restaurant.average_rating = calculate_average_rating(restaurant_ratings)
#         restaurant.rating_count = len(restaurant_ratings)
#         restaurants_db[restaurant_id] = restaurant
    
#     return None

# Add these new endpoints after the existing rating endpoints

# @app.get("/ratings", response_model=List[Rating], tags=["Ratings"])
# async def get_ratings(
#     food_item_id: Optional[str] = None,
#     restaurant_id: Optional[str] = None,
#     min_rating: Optional[float] = None,
#     max_rating: Optional[float] = None,
#     start_date: Optional[datetime] = None,
#     end_date: Optional[datetime] = None,
#     sort_by: Optional[str] = "recent",  # recent, highest, lowest, most_helpful
#     has_response: Optional[bool] = None,
#     keywords: Optional[List[str]] = Query(None),
#     skip: int = 0,
#     limit: int = 20,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Get ratings with advanced filtering and pagination"""
#     filtered_ratings = list(ratings_db.values())
    
#     # Apply filters
#     if food_item_id:
#         filtered_ratings = [r for r in filtered_ratings if r.food_item_id == food_item_id]
    
#     if restaurant_id:
#         filtered_ratings = [r for r in filtered_ratings if r.restaurant_id == restaurant_id]
    
#     if min_rating:
#         filtered_ratings = [r for r in filtered_ratings if r.rating >= min_rating]
    
#     if max_rating:
#         filtered_ratings = [r for r in filtered_ratings if r.rating <= max_rating]
    
#     if start_date:
#         filtered_ratings = [r for r in filtered_ratings if r.created_at >= start_date]
    
#     if end_date:
#         filtered_ratings = [r for r in filtered_ratings if r.created_at <= end_date]
    
#     if has_response is not None:
#         # Check if the rating has a response
#         ratings_with_responses = [r.rating_id for r in review_responses_db.values()]
#         if has_response:
#             filtered_ratings = [r for r in filtered_ratings if r.id in ratings_with_responses]
#         else:
#             filtered_ratings = [r for r in filtered_ratings if r.id not in ratings_with_responses]
    
#     if keywords:
#         # Filter ratings that contain any of the keywords in the review
#         filtered_ratings = [
#             r for r in filtered_ratings 
#             if r.review and any(keyword.lower() in r.review.lower() for keyword in keywords)
#         ]
    
#     # Apply sorting
#     if sort_by == "recent":
#         filtered_ratings.sort(key=lambda r: r.created_at, reverse=True)
#     elif sort_by == "highest":
#         filtered_ratings.sort(key=lambda r: r.rating, reverse=True)
#     elif sort_by == "lowest":
#         filtered_ratings.sort(key=lambda r: r.rating)
#     elif sort_by == "most_helpful":
#         # Sort by the number of helpful votes
#         def get_helpful_votes(rating):
#             return len([
#                 v for v in review_votes_db.values() 
#                 if v.rating_id == rating.id and v.vote_type == ReviewVoteType.HELPFUL
#             ])
#         filtered_ratings.sort(key=get_helpful_votes, reverse=True)
    
#     # Apply pagination
#     paginated_ratings = filtered_ratings[skip:skip + limit]
    
#     return paginated_ratings

# @app.post("/ratings/{rating_id}/votes", response_model=ReviewVote, tags=["Ratings"])
# async def vote_on_rating(
#     rating_id: str,
#     vote: ReviewVoteCreate,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Vote on a rating as helpful or unhelpful"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     # Check if user has already voted on this rating
#     for v in review_votes_db.values():
#         if v.user_id == current_user.id and v.rating_id == rating_id:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="You have already voted on this rating"
#             )
    
#     # Create new vote
#     vote_id = str(uuid.uuid4())
    
#     db_vote = ReviewVote(
#         id=vote_id,
#         user_id=current_user.id,
#         rating_id=rating_id,
#         vote_type=vote.vote_type,
#         created_at=datetime.now()
#     )
    
#     review_votes_db[vote_id] = db_vote
#     return db_vote

# @app.delete("/ratings/{rating_id}/votes", status_code=status.HTTP_204_NO_CONTENT, tags=["Ratings"])
# async def remove_vote(
#     rating_id: str,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Remove your vote from a rating"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     # Find user's vote on this rating
#     user_vote = None
#     user_vote_id = None
    
#     for vote_id, vote in review_votes_db.items():
#         if vote.user_id == current_user.id and vote.rating_id == rating_id:
#             user_vote = vote
#             user_vote_id = vote_id
#             break
    
#     if not user_vote:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="You have not voted on this rating"
#         )
    
#     # Delete the vote
#     del review_votes_db[user_vote_id]
#     return None

# @app.get("/ratings/{rating_id}/votes", response_model=Dict[str, int], tags=["Ratings"])
# async def get_rating_votes(
#     rating_id: str,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Get the vote counts for a rating"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     # Count votes by type
#     helpful_votes = len([
#         v for v in review_votes_db.values() 
#         if v.rating_id == rating_id and v.vote_type == ReviewVoteType.HELPFUL
#     ])
    
#     unhelpful_votes = len([
#         v for v in review_votes_db.values() 
#         if v.rating_id == rating_id and v.vote_type == ReviewVoteType.UNHELPFUL
#     ])
    
#     # Check if current user has voted
#     user_vote = None
#     for vote in review_votes_db.values():
#         if vote.user_id == current_user.id and vote.rating_id == rating_id:
#             user_vote = vote.vote_type
#             break
    
#     return {
#         "helpful": helpful_votes,
#         "unhelpful": unhelpful_votes,
#         "user_vote": user_vote
#     }

# @app.post("/ratings/{rating_id}/report", response_model=ReviewReport, tags=["Ratings"])
# async def report_rating(
#     rating_id: str,
#     report: ReviewReportCreate,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Report a rating for inappropriate content"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     # Check if user has already reported this rating
#     for r in review_reports_db.values():
#         if r.user_id == current_user.id and r.rating_id == rating_id:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="You have already reported this rating"
#             )
    
#     # Create new report
#     report_id = str(uuid.uuid4())
    
#     db_report = ReviewReport(
#         id=report_id,
#         user_id=current_user.id,
#         rating_id=rating_id,
#         reason=report.reason,
#         description=report.description,
#         status="pending",
#         created_at=datetime.now(),
#         updated_at=None
#     )
    
#     review_reports_db[report_id] = db_report
#     return db_report

# @app.get("/admin/reports", response_model=List[ReviewReport], tags=["Admin"])
# async def get_reports(
#     status: Optional[str] = None,
#     current_user: User = Depends(get_admin_user)
# ):
#     """Get all rating reports (admin only)"""
#     reports = list(review_reports_db.values())
    
#     if status:
#         reports = [r for r in reports if r.status == status]
    
#     return reports

# @app.put("/admin/reports/{report_id}", response_model=ReviewReport, tags=["Admin"])
# async def update_report_status(
#     report_id: str,
#     status: str,
#     current_user: User = Depends(get_admin_user)
# ):
#     """Update the status of a report (admin only)"""
#     if report_id not in review_reports_db:
#         raise HTTPException(status_code=404, detail="Report not found")
    
#     if status not in ["pending", "reviewed", "dismissed"]:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid status. Must be one of: pending, reviewed, dismissed"
#         )
    
#     report = review_reports_db[report_id]
#     report.status = status
#     report.updated_at = datetime.now()
    
#     review_reports_db[report_id] = report
#     return report

# @app.post("/ratings/{rating_id}/response", response_model=ReviewResponse, tags=["Ratings"])
# async def respond_to_rating(
#     rating_id: str,
#     response: ReviewResponseCreate,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Respond to a rating (restaurant owners or admins)"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     rating = ratings_db[rating_id]
    
#     # Check if the rating is for a restaurant and the current user is authorized to respond
#     is_authorized = False
    
#     # Admin can respond to any rating
#     if current_user.role == UserRole.ADMIN:
#         is_authorized = True
    
#     # Restaurant owner can respond to ratings for their restaurant
#     elif rating.restaurant_id:
#         restaurant = restaurants_db.get(rating.restaurant_id)
#         if restaurant and restaurant.created_by == current_user.id:
#             is_authorized = True
    
#     if not is_authorized:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You are not authorized to respond to this rating"
#         )
    
#     # Check if a response already exists
#     for resp in review_responses_db.values():
#         if resp.rating_id == rating_id:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="A response already exists for this rating"
#             )
    
#     # Create new response
#     response_id = str(uuid.uuid4())
    
#     db_response = ReviewResponse(
#         id=response_id,
#         rating_id=rating_id,
#         user_id=current_user.id,
#         response_text=response.response_text,
#         created_at=datetime.now(),
#         updated_at=None
#     )
    
#     review_responses_db[response_id] = db_response
#     return db_response

# @app.put("/ratings/{rating_id}/response", response_model=ReviewResponse, tags=["Ratings"])
# async def update_rating_response(
#     rating_id: str,
#     response: ReviewResponseCreate,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Update a response to a rating"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     # Find the existing response
#     existing_response = None
#     response_id = None
    
#     for resp_id, resp in review_responses_db.items():
#         if resp.rating_id == rating_id:
#             existing_response = resp
#             response_id = resp_id
#             break
    
#     if not existing_response:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No response exists for this rating"
#         )
    
#     # Check if the current user is authorized to update the response
#     if existing_response.user_id != current_user.id and current_user.role != UserRole.ADMIN:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You are not authorized to update this response"
#         )
    
#     # Update the response
#     existing_response.response_text = response.response_text
#     existing_response.updated_at = datetime.now()
    
#     review_responses_db[response_id] = existing_response
#     return existing_response

# @app.get("/ratings/{rating_id}/response", response_model=ReviewResponse, tags=["Ratings"])
# async def get_rating_response(
#     rating_id: str,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Get the response to a rating"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     # Find the response
#     for resp in review_responses_db.values():
#         if resp.rating_id == rating_id:
#             return resp
    
#     raise HTTPException(
#         status_code=status.HTTP_404_NOT_FOUND,
#         detail="No response exists for this rating"
#     )

# @app.delete("/ratings/{rating_id}/response", status_code=status.HTTP_204_NO_CONTENT, tags=["Ratings"])
# async def delete_rating_response(
#     rating_id: str
#     # current_user: User = Depends(get_current_active_user)
# ):
#     """Delete a response to a rating"""
#     if rating_id not in ratings_db:
#         raise HTTPException(status_code=404, detail="Rating not found")
    
#     # Find the response
#     response_to_delete = None
#     response_id = None
    
#     for resp_id, resp in review_responses_db.items():
#         if resp.rating_id == rating_id:
#             response_to_delete = resp
#             response_id = resp_id
#             break
    
#     if not response_to_delete:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No response exists for this rating"
#         )
    
#     # Check if the current user is authorized to delete the response
#     if response_to_delete.user_id != current_user.id and current_user.role != UserRole.ADMIN:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You are not authorized to delete this response"
#         )
    
#     # Delete the response
#     del review_responses_db[response_id]
#     return None

# @app.get("/food-items/{food_id}/review-analytics", response_model=ReviewAnalytics, tags=["Analytics"])
# async def get_food_review_analytics(
#     food_id: str
# ):
#     """Get analytics for reviews of a specific food item"""
#     if food_id not in food_items_db:
#         raise HTTPException(status_code=404, detail="Food item not found")
    
#     # Get all ratings for this food item
#     food_ratings = [r for r in ratings_db.values() if r.food_item_id == food_id]
    
#     if not food_ratings:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No reviews found for this food item"
#         )
    
#     # Calculate total reviews and average rating
#     total_reviews = len(food_ratings)
#     average_rating = sum(r.rating for r in food_ratings) / total_reviews
    
#     # Calculate rating distribution
#     rating_distribution = {
#         "1": len([r for r in food_ratings if r.rating == 1.0]),
#         "2": len([r for r in food_ratings if r.rating == 2.0]),
#         "3": len([r for r in food_ratings if r.rating == 3.0]),
#         "4": len([r for r in food_ratings if r.rating == 4.0]),
#         "5": len([r for r in food_ratings if r.rating == 5.0])
#     }
    
#     # Calculate recent trend (change in average rating over last 30 days)
#     thirty_days_ago = datetime.now() - timedelta(days=30)
#     recent_ratings = [r for r in food_ratings if r.created_at >= thirty_days_ago]
#     older_ratings = [r for r in food_ratings if r.created_at < thirty_days_ago]
    
#     recent_avg = sum(r.rating for r in recent_ratings) / len(recent_ratings) if recent_ratings else 0
#     older_avg = sum(r.rating for r in older_ratings) / len(older_ratings) if older_ratings else 0
    
#     recent_trend = recent_avg - older_avg if older_ratings else 0
    
#     # Extract most mentioned keywords from reviews
#     all_review_text = " ".join([r.review for r in food_ratings if r.review])
    
#     # Simple keyword extraction (in a real app, you'd use NLP)
#     words = re.findall(r'\b[a-zA-Z]{3,}\b', all_review_text.lower())
#     word_counts = Counter(words)
    
#     # Filter out common stop words (simplified)
#     stop_words = {"the", "and", "was", "for", "this", "that", "with", "very", "just"}
#     filtered_words = {word: count for word, count in word_counts.items() if word not in stop_words}
    
#     # Get top 10 keywords
#     most_mentioned = [{"word": word, "count": count} 
#                      for word, count in sorted(filtered_words.items(), key=lambda x: x[1], reverse=True)[:10]]
    
#     return ReviewAnalytics(
#         total_reviews=total_reviews,
#         average_rating=average_rating,
#         rating_distribution=rating_distribution,
#         recent_trend=recent_trend,
#         most_mentioned_keywords=most_mentioned
#     )

# @app.get("/restaurants/{restaurant_id}/review-analytics", response_model=ReviewAnalytics, tags=["Analytics"])
# async def get_restaurant_review_analytics(
#     restaurant_id: str,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Get analytics for reviews of a specific restaurant"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     # Get all ratings for this restaurant
#     restaurant_ratings = [r for r in ratings_db.values() if r.restaurant_id == restaurant_id]
    
#     if not restaurant_ratings:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No reviews found for this restaurant"
#         )
    
#     # Calculate total reviews and average rating
#     total_reviews = len(restaurant_ratings)
#     average_rating = sum(r.rating for r in restaurant_ratings) / total_reviews
    
#     # Calculate rating distribution
#     rating_distribution = {
#         "1": len([r for r in restaurant_ratings if r.rating == 1.0]),
#         "2": len([r for r in restaurant_ratings if r.rating == 2.0]),
#         "3": len([r for r in restaurant_ratings if r.rating == 3.0]),
#         "4": len([r for r in restaurant_ratings if r.rating == 4.0]),
#         "5": len([r for r in restaurant_ratings if r.rating == 5.0])
#     }
    
#     # Calculate recent trend (change in average rating over last 30 days)
#     thirty_days_ago = datetime.now() - timedelta(days=30)
#     recent_ratings = [r for r in restaurant_ratings if r.created_at >= thirty_days_ago]
#     older_ratings = [r for r in restaurant_ratings if r.created_at < thirty_days_ago]
    
#     recent_avg = sum(r.rating for r in recent_ratings) / len(recent_ratings) if recent_ratings else 0
#     older_avg = sum(r.rating for r in older_ratings) / len(older_ratings) if older_ratings else 0
    
#     recent_trend = recent_avg - older_avg if older_ratings else 0
    
#     # Extract most mentioned keywords from reviews
#     all_review_text = " ".join([r.review for r in restaurant_ratings if r.review])
    
#     # Simple keyword extraction (in a real app, you'd use NLP)
#     words = re.findall(r'\b[a-zA-Z]{3,}\b', all_review_text.lower())
#     word_counts = Counter(words)
    
#     # Filter out common stop words (simplified)
#     stop_words = {"the", "and", "was", "for", "this", "that", "with", "very", "just"}
#     filtered_words = {word: count for word, count in word_counts.items() if word not in stop_words}
    
#     # Get top 10 keywords
#     most_mentioned = [{"word": word, "count": count} 
#                      for word, count in sorted(filtered_words.items(), key=lambda x: x[1], reverse=True)[:10]]
    
#     return ReviewAnalytics(
#         total_reviews=total_reviews,
#         average_rating=average_rating,
#         rating_distribution=rating_distribution,
#         recent_trend=recent_trend,
#         most_mentioned_keywords=most_mentioned
#     )

# # Wishlist endpoints
# @app.get("/wishlist", response_model=List[Dict[str, Any]], tags=["Wishlist"])
# async def get_wishlist(current_user: User = Depends(get_current_active_user)):
#     """Get the current user's wishlist with detailed information"""
#     user_wishlist = [item for item in wishlist_db.values() if item.user_id == current_user.id]
    
#     detailed_wishlist = []
#     for item in user_wishlist:
#         wishlist_item = {
#             "id": item.id,
#             "added_at": item.added_at,
#             "type": "food" if item.food_item_id else "restaurant"
#         }
        
#         if item.food_item_id:
#             food_item = food_items_db.get(item.food_item_id)
#             if food_item:
#                 wishlist_item["item"] = food_item
        
#         if item.restaurant_id:
#             restaurant = restaurants_db.get(item.restaurant_id)
#             if restaurant:
#                 wishlist_item["item"] = restaurant
        
#         detailed_wishlist.append(wishlist_item)
    
#     return detailed_wishlist

# @app.post("/wishlist", response_model=WishlistItem, status_code=status.HTTP_201_CREATED, tags=["Wishlist"])
# async def add_to_wishlist(wishlist_item: WishlistItemCreate, current_user: User = Depends(get_current_active_user)):
#     """Add an item to the current user's wishlist"""
#     # Validate that at least one of food_item_id or restaurant_id is provided
#     if not wishlist_item.food_item_id and not wishlist_item.restaurant_id:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Either food_item_id or restaurant_id must be provided"
#         )
    
#     # Validate that the food item or restaurant exists
#     if wishlist_item.food_item_id and wishlist_item.food_item_id not in food_items_db:
#         raise HTTPException(status_code=404, detail="Food item not found")
    
#     if wishlist_item.restaurant_id and wishlist_item.restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     # Check if the item is already in the wishlist
#     for item in wishlist_db.values():
#         if item.user_id == current_user.id:
#             if (wishlist_item.food_item_id and item.food_item_id == wishlist_item.food_item_id) or \
#                (wishlist_item.restaurant_id and item.restaurant_id == wishlist_item.restaurant_id):
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Item already in wishlist"
#                 )
    
#     wishlist_id = str(uuid.uuid4())
    
#     db_wishlist_item = WishlistItem(
#         id=wishlist_id,
#         user_id=current_user.id,
#         **wishlist_item.dict(),
#         added_at=datetime.now()
#     )
    
#     wishlist_db[wishlist_id] = db_wishlist_item
#     return db_wishlist_item

# @app.delete("/wishlist/{wishlist_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Wishlist"])
# async def remove_from_wishlist(wishlist_id: str, current_user: User = Depends(get_current_active_user)):
#     """Remove an item from the current user's wishlist"""
#     if wishlist_id not in wishlist_db:
#         raise HTTPException(status_code=404, detail="Wishlist item not found")
    
#     # Check if the wishlist item belongs to the current user
#     if wishlist_db[wishlist_id].user_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Not enough permissions")
    
#     del wishlist_db[wishlist_id]
#     return None

# Recommendation endpoints
# @app.get("/recommendations", response_model=RecommendationResponse, tags=["Recommendations"])
# async def get_recommendations(
#     cuisine: Optional[Cuisine] = Query(None, description="Filter by cuisine type"),
#     dietary_preference: Optional[List[DietaryPreference]] = Query(None, description="Filter by dietary preferences"),
#     meal_type: Optional[MealType] = Query(None, description="Filter by meal type"),
#     category: Optional[ItemCategory] = Query(None, description="Filter by item category"),
#     max_calories: Optional[int] = Query(None, description="Maximum calories"),
#     max_preparation_time: Optional[int] = Query(None, description="Maximum preparation time in minutes"),
#     time_of_day: Optional[str] = Query(None, description="Current time of day (morning, afternoon, evening)"),
#     sort_by: Optional[SortOption] = Query(SortOption.RELEVANCE, description="Sort option"),
#     limit: int = Query(5, description="Maximum number of recommendations to return"),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Get food recommendations based on filters, time of day, and user preferences"""
#     filtered_items = list(food_items_db.values())
    
#     # Apply filters
#     if cuisine:
#         filtered_items = [item for item in filtered_items if item.cuisine == cuisine]
    
#     if dietary_preference:
#         filtered_items = [
#             item for item in filtered_items 
#             if all(pref in item.dietary_preferences for pref in dietary_preference)
#         ]
    
#     if meal_type:
#         filtered_items = [item for item in filtered_items if meal_type in item.meal_types]
    
#     if category:
#         filtered_items = [item for item in filtered_items if item.category == category]
    
#     if max_calories:
#         filtered_items = [item for item in filtered_items if item.calories and item.calories <= max_calories]
    
#     if max_preparation_time:
#         filtered_items = [item for item in filtered_items if item.preparation_time_minutes and item.preparation_time_minutes <= max_preparation_time]
    
#     # Apply time of day logic if provided
#     if time_of_day:
#         if time_of_day.lower() == "morning":
#             filtered_items = [item for item in filtered_items if MealType.BREAKFAST in item.meal_types]
#         elif time_of_day.lower() == "afternoon":
#             filtered_items = [item for item in filtered_items if MealType.LUNCH in item.meal_types]
#         elif time_of_day.lower() == "evening":
#             filtered_items = [item for item in filtered_items if MealType.DINNER in item.meal_types]
    
#     # Apply user preferences
#     user_preferences = current_user.preferences
    
#     # Apply dietary preferences from user profile if not specified in request
#     if not dietary_preference and user_preferences.dietary_preferences:
#         filtered_items = [
#             item for item in filtered_items 
#             if all(pref in item.dietary_preferences for pref in user_preferences.dietary_preferences)
#         ]
    
#     # Prioritize user's favorite cuisines if not specified in request
#     if not cuisine and user_preferences.favorite_cuisines:
#         filtered_items.sort(
#             key=lambda item: item.cuisine in user_preferences.favorite_cuisines, 
#             reverse=True
#         )
    
#     # Get user's wishlist to prioritize similar items
#     user_wishlist = [item for item in wishlist_db.values() if item.user_id == current_user.id]
#     wishlist_food_ids = [item.food_item_id for item in user_wishlist if item.food_item_id]
    
#     # Get user's ratings to prioritize similar items to highly rated ones
#     user_ratings = [rating for rating in ratings_db.values() if rating.user_id == current_user.id]
#     highly_rated_food_ids = [
#         rating.food_item_id for rating in user_ratings 
#         if rating.food_item_id and rating.rating >= 4.0
#     ]
    
#     # Apply sorting based on sort_by parameter
#     if sort_by == SortOption.RATING:
#         filtered_items.sort(key=lambda x: x.average_rating if x.average_rating else 0, reverse=True)
#     elif sort_by == SortOption.TRENDING:
#         filtered_items.sort(key=lambda x: (x.is_trending, x.popularity_score), reverse=True)
#     elif sort_by == SortOption.PRICE_LOW:
#         filtered_items.sort(key=lambda x: x.price if x.price else float('inf'))
#     elif sort_by == SortOption.PRICE_HIGH:
#         filtered_items.sort(key=lambda x: x.price if x.price else 0, reverse=True)
#     elif sort_by == SortOption.NEWEST:
#         filtered_items.sort(key=lambda x: x.created_at, reverse=True)
    
#     # Prioritize items similar to those in the user's wishlist and highly rated items
#     if wishlist_food_ids or highly_rated_food_ids:
#         # Get cuisines from wishlist and highly rated items
#         wishlist_cuisines = [
#             food_items_db[food_id].cuisine 
#             for food_id in wishlist_food_ids + highly_rated_food_ids 
#             if food_id in food_items_db
#         ]
        
#         # Sort filtered items to prioritize those with matching cuisines
#         if wishlist_cuisines and sort_by == SortOption.RELEVANCE:
#             filtered_items.sort(key=lambda item: item.cuisine in wishlist_cuisines, reverse=True)
    
#     # Randomize and limit results
#     if len(filtered_items) > limit:
#         # Keep the prioritized items at the top, but randomize the rest
#         top_items = filtered_items[:limit//2]
#         rest_items = filtered_items[limit//2:]
#         random_rest = random.sample(rest_items, min(limit - len(top_items), len(rest_items)))
#         filtered_items = top_items + random_rest
    
#     return RecommendationResponse(
#         recommendations=filtered_items[:limit],
#         count=len(filtered_items[:limit])
#     )

# @app.post("/recommendations", response_model=RecommendationResponse, tags=["Recommendations"])
# async def post_recommendations(
#     request: RecommendationRequest, 
#     limit: int = Query(5)
#     # current_user: User = Depends(get_current_active_user)
# ):
#     """Get food recommendations based on request body"""
#     filtered_items = list(food_items_db.values())
    
#     # Apply filters
#     if request.cuisine:
#         filtered_items = [item for item in filtered_items if item.cuisine == request.cuisine]
    
#     if request.dietary_preferences:
#         filtered_items = [
#             item for item in filtered_items 
#             if all(pref in item.dietary_preferences for pref in request.dietary_preferences)
#         ]
    
#     if request.meal_type:
#         filtered_items = [item for item in filtered_items if request.meal_type in item.meal_types]
    
#     if request.max_calories:
#         filtered_items = [item for item in filtered_items if item.calories and item.calories <= request.max_calories]
    
#     if request.max_preparation_time:
#         filtered_items = [item for item in filtered_items if item.preparation_time_minutes and item.preparation_time_minutes <= request.max_preparation_time]
    
#     # Apply time of day logic if provided
#     if request.time_of_day:
#         if request.time_of_day.lower() == "morning":
#             filtered_items = [item for item in filtered_items if MealType.BREAKFAST in item.meal_types]
#         elif request.time_of_day.lower() == "afternoon":
#             filtered_items = [item for item in filtered_items if MealType.LUNCH in item.meal_types]
#         elif request.time_of_day.lower() == "evening":
#             filtered_items = [item for item in filtered_items if MealType.DINNER in item.meal_types]
    
#     # Apply user preferences
#     # user_preferences = current_user.preferences
    
#     # Apply dietary preferences from user profile if not specified in request
#     if not request.dietary_preferences and user_preferences.dietary_preferences:
#         filtered_items = [
#             item for item in filtered_items 
#             if all(pref in item.dietary_preferences for pref in user_preferences.dietary_preferences)
#         ]
    
#     # Prioritize items similar to previously liked items
#     if request.previous_liked:
#         # Get cuisines from liked items
#         liked_cuisines = [food_items_db[food_id].cuisine for food_id in request.previous_liked if food_id in food_items_db]
        
#         # Sort filtered items to prioritize those with matching cuisines
#         if liked_cuisines and request.sort_by == SortOption.RELEVANCE:
#             filtered_items.sort(key=lambda item: item.cuisine in liked_cuisines, reverse=True)
    
#     # Apply sorting based on sort_by parameter
#     if request.sort_by == SortOption.RATING:
#         filtered_items.sort(key=lambda x: x.average_rating if x.average_rating else 0, reverse=True)
#     elif request.sort_by == SortOption.TRENDING:
#         filtered_items.sort(key=lambda x: (x.is_trending, x.popularity_score), reverse=True)
#     elif request.sort_by == SortOption.PRICE_LOW:
#         filtered_items.sort(key=lambda x: x.price if x.price else float('inf'))
#     elif request.sort_by == SortOption.PRICE_HIGH:
#         filtered_items.sort(key=lambda x: x.price if x.price else 0, reverse=True)
#     elif request.sort_by == SortOption.NEWEST:
#         filtered_items.sort(key=lambda x: x.created_at, reverse=True)
    
#     # Randomize and limit results
#     if len(filtered_items) > limit:
#         # Keep the prioritized items at the top, but randomize the rest
#         top_items = filtered_items[:limit//2]
#         rest_items = filtered_items[limit//2:]
#         random_rest = random.sample(rest_items, min(limit - len(top_items), len(rest_items)))
#         filtered_items = top_items + random_rest
    
#     return RecommendationResponse(
#         recommendations=filtered_items[:limit],
#         count=len(filtered_items[:limit])
#     )

# @app.get("/trending", response_model=TrendingResponse, tags=["Recommendations"])
# async def get_trending_items():
#     """Get trending food items and restaurants"""
#     trending_foods = [item for item in food_items_db.values() if item.is_trending]
#     trending_restaurants = [restaurant for restaurant in restaurants_db.values() if restaurant.is_trending]
    
#     # Sort by popularity score
#     trending_foods.sort(key=lambda x: x.popularity_score, reverse=True)
#     trending_restaurants.sort(key=lambda x: x.popularity_score, reverse=True)
    
#     # Limit to top 10 of each
#     trending_foods = trending_foods[:10]
#     trending_restaurants = trending_restaurants[:10]
    
#     return TrendingResponse(
#         trending_foods=trending_foods,
#         trending_restaurants=trending_restaurants
#     )

# @app.get("/top-rated", response_model=Dict[str, List], tags=["Recommendations"])
# async def get_top_rated_items(current_user: User = Depends(get_current_active_user)):
#     """Get top-rated food items and restaurants"""
#     # Get all food items and restaurants with ratings
#     rated_foods = [item for item in food_items_db.values() if item.average_rating is not None]
#     rated_restaurants = [restaurant for restaurant in restaurants_db.values() if restaurant.average_rating is not None]
    
#     # Sort by rating
#     rated_foods.sort(key=lambda x: (x.average_rating, x.rating_count), reverse=True)
#     rated_restaurants.sort(key=lambda x: (x.average_rating, x.rating_count), reverse=True)
    
#     # Limit to top 10 of each
#     top_rated_foods = rated_foods[:10]
#     top_rated_restaurants = rated_restaurants[:10]
    
#     return {
#         "top_rated_foods": top_rated_foods,
#         "top_rated_restaurants": top_rated_restaurants
#     }

# @app.get("/random", response_model=FoodItem, tags=["Recommendations"])
# async def get_random_food(current_user: User = Depends(get_current_active_user)):
#     """Get a random food recommendation"""
#     return random.choice(list(food_items_db.values()))

# @app.post("/search", response_model=Dict[str, List], tags=["Search"])
# async def search(
#     request: SearchRequest,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Search for food items and restaurants"""
#     # Search food items
#     food_items = list(food_items_db.values())
    
#     # Apply filters to food items
#     if request.cuisines:
#         food_items = [item for item in food_items if item.cuisine in request.cuisines]
    
#     if request.dietary_preferences:
#         food_items = [
#             item for item in food_items 
#             if all(pref in item.dietary_preferences for pref in request.dietary_preferences)
#         ]
    
#     if request.meal_types:
#         food_items = [
#             item for item in food_items 
#             if any(meal_type in item.meal_types for meal_type in request.meal_types)
#         ]
    
#     if request.categories:
#         food_items = [
#             item for item in food_items 
#             if item.category in request.categories
#         ]
    
#     if request.max_calories:
#         food_items = [item for item in food_items if item.calories and item.calories <= request.max_calories]
    
#     if request.max_preparation_time:
#         food_items = [item for item in food_items if item.preparation_time_minutes and item.preparation_time_minutes <= request.max_preparation_time]
    
#     if request.min_rating:
#         food_items = [item for item in food_items if item.average_rating and item.average_rating >= request.min_rating]
    
#     # Search restaurants
#     restaurants = list(restaurants_db.values())
    
#     # Apply filters to restaurants
#     if request.cuisines:
#         restaurants = [
#             restaurant for restaurant in restaurants 
#             if any(cuisine in restaurant.cuisine_types for cuisine in request.cuisines)
#         ]
    
#     if request.price_range:
#         restaurants = [
#             restaurant for restaurant in restaurants 
#             if restaurant.price_range in request.price_range
#         ]
    
#     if request.min_rating:
#         restaurants = [
#             restaurant for restaurant in restaurants 
#             if restaurant.average_rating and restaurant.average_rating >= request.min_rating
#         ]
    
#     # Apply text search if query is provided
#     if request.query:
#         query = request.query.lower()
        
#         # Search food items
#         food_items = [
#             item for item in food_items 
#             if query in item.name.lower() or 
#             query in item.description.lower() or 
#             any(query in ingredient.lower() for ingredient in item.ingredients)
#         ]
        
#         # Search restaurants
#         restaurants = [
#             restaurant for restaurant in restaurants 
#             if query in restaurant.name.lower() or 
#             query in restaurant.description.lower() or
#             query in restaurant.city.lower() or 
#             query in restaurant.address.lower()
#         ]
    
#     # Apply sorting based on sort_by parameter
#     if request.sort_by == SortOption.RATING:
#         food_items.sort(key=lambda x: x.average_rating if x.average_rating else 0, reverse=True)
#         restaurants.sort(key=lambda x: x.average_rating if x.average_rating else 0, reverse=True)
#     elif request.sort_by == SortOption.TRENDING:
#         food_items.sort(key=lambda x: (x.is_trending, x.popularity_score), reverse=True)
#         restaurants.sort(key=lambda x: (x.is_trending, x.popularity_score), reverse=True)
#     elif request.sort_by == SortOption.PRICE_LOW:
#         food_items.sort(key=lambda x: x.price if x.price else float('inf'))
#         restaurants.sort(key=lambda x: {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4}[x.price_range])
#     elif request.sort_by == SortOption.PRICE_HIGH:
#         food_items.sort(key=lambda x: x.price if x.price else 0, reverse=True)
#         restaurants.sort(key=lambda x: {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4}[x.price_range], reverse=True)
#     elif request.sort_by == SortOption.NEWEST:
#         food_items.sort(key=lambda x: x.created_at, reverse=True)
#         restaurants.sort(key=lambda x: x.created_at, reverse=True)
    
#     return {
#         "food_items": food_items,
#         "restaurants": restaurants
#     }




# In-memory databases (replace with actual database in production)
reviews_db = {}
review_votes_db = {}
review_reports_db = {}
review_responses_db = {}

# Create a review
@app.post("/reviews", response_model=Review, status_code=201, tags=["Reviews"])
async def create_review(
    review: ReviewCreate
    # current_user: User = Depends(get_current_active_user)
):
    """Create a new review."""
    review_id = str(uuid4())
    new_review = Review(
        id=review_id,
        food_item_id=review.food_item_id,
        # user_id=current_user.id,
        rating=review.rating,
        comment=review.comment,
        created_at=datetime.now(),
        updated_at=None
    )
    reviews_db[review_id] = new_review
    return new_review


# Get all reviews
@app.get("/reviews", response_model=List[Review], tags=["Reviews"])
async def get_all_reviews():
    """Retrieve all reviews."""
    return list(reviews_db.values())


# Get a specific review
@app.get("/reviews/{review_id}", response_model=Review, tags=["Reviews"])
async def get_review(review_id: str):
    """Retrieve a specific review by ID."""
    if review_id not in reviews_db:
        raise HTTPException(status_code=404, detail="Review not found")
    return reviews_db[review_id]


# # Create a review vote
# @app.post("/reviews/{review_id}/votes", response_model=ReviewVote, status_code=201, tags=["Review Votes"])
# async def create_review_vote(
#     review_id: str,
#     vote: ReviewVoteCreate,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Vote on a review."""
#     if review_id not in reviews_db:
#         raise HTTPException(status_code=404, detail="Review not found")
#     vote_id = str(uuid4())
#     new_vote = ReviewVote(
#         id=vote_id,
#         user_id=current_user.id,
#         rating_id=review_id,
#         vote_type=vote.vote_type,
#         created_at=datetime.now()
#     )
#     review_votes_db[vote_id] = new_vote
#     return new_vote


# Report a review
# @app.post("/reviews/{review_id}/reports", response_model=ReviewReport, status_code=201, tags=["Review Reports"])
# async def report_review(
#     review_id: str,
#     report: ReviewReportCreate,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Report a review."""
#     if review_id not in reviews_db:
#         raise HTTPException(status_code=404, detail="Review not found")
#     report_id = str(uuid4())
#     new_report = ReviewReport(
#         id=report_id,
#         user_id=current_user.id,
#         rating_id=review_id,
#         reason=report.reason,
#         description=report.description,
#         status="pending",
#         created_at=datetime.now(),
#         updated_at=None
#     )
#     review_reports_db[report_id] = new_report
#     return new_report


# Respond to a review
# @app.post("/reviews/{review_id}/responses", response_model=ReviewResponse, status_code=201, tags=["Review Responses"])
# async def respond_to_review(
#     review_id: str,
#     response: ReviewResponseCreate,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Respond to a review."""
#     if review_id not in reviews_db:
#         raise HTTPException(status_code=404, detail="Review not found")
#     response_id = str(uuid4())
#     new_response = ReviewResponse(
#         id=response_id,
#         rating_id=review_id,
#         user_id=current_user.id,
#         response_text=response.response_text,
#         created_at=datetime.now(),
#         updated_at=None
#     )
#     review_responses_db[response_id] = new_response
#     return new_response


# Get analytics for reviews
@app.get("/reviews/analytics", response_model=ReviewAnalytics, tags=["Review Analytics"])
async def get_review_analytics():
    """Get analytics for reviews."""
    total_reviews = len(reviews_db)
    if total_reviews == 0:
        return ReviewAnalytics(
            total_reviews=0,
            average_rating=0.0,
            rating_distribution={},
            recent_trend=0.0,
            most_mentioned_keywords=[]
        )
    average_rating = sum(review.rating for review in reviews_db.values()) / total_reviews
    rating_distribution = Counter(str(review.rating) for review in reviews_db.values())
    # Example: Add logic for recent_trend and most_mentioned_keywords if needed
    return ReviewAnalytics(
        total_reviews=total_reviews,
        average_rating=average_rating,
        rating_distribution=dict(rating_distribution),
        recent_trend=0.0,
        most_mentioned_keywords=[]
    )


# File upload endpoints
@app.post("/upload/food-image/{food_id}", response_model=FileMetadata, tags=["Files"])
async def upload_food_image(
    food_id: str,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None)
):
    """Upload an image for a food item"""
    if food_id not in food_items_db:
        raise HTTPException(status_code=404, detail="Food item not found")
    
   
    
    file_metadata = await save_upload_file(
        upload_file=file,
        category="food_images",
        related_id=food_id,
        description=description
    )
    
    # Update the food item with the new image URL
    food_item = food_items_db[food_id]
    food_item.image_url = file_metadata.url
    food_items_db[food_id] = food_item
    
    return file_metadata

# @app.post("/upload/restaurant-image/{restaurant_id}", response_model=FileMetadata, tags=["Files"])
# async def upload_restaurant_image(
#     restaurant_id: str,
#     file: UploadFile = File(...),
#     description: Optional[str] = Form(None),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Upload an image for a restaurant"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     # Check if user is admin or the creator of the restaurant
#     if current_user.role != UserRole.ADMIN and restaurants_db[restaurant_id].created_by != current_user.id:
#         raise HTTPException(status_code=403, detail="Not enough permissions")
    
#     file_metadata = await save_upload_file(
#         upload_file=file,
#         category="restaurant_images",
#         user_id=current_user.id,
#         related_id=restaurant_id,
#         description=description
#     )
    
#     # Update the restaurant with the new image URL
#     restaurant = restaurants_db[restaurant_id]
#     restaurant.image_url = file_metadata.url
#     restaurants_db[restaurant_id] = restaurant
    
#     return file_metadata

# @app.post("/upload/user-image", response_model=FileMetadata, tags=["Files"])
# async def upload_user_image(
#     file: UploadFile = File(...),
#     description: Optional[str] = Form(None),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Upload a profile image for the current user"""
#     file_metadata = await save_upload_file(
#         upload_file=file,
#         category="user_images",
#         user_id=current_user.id,
#         related_id=current_user.id,
#         description=description
#     )
    
#     # Update the user with the new profile picture URL
#     user = users_db[current_user.username]
#     user.profile_picture = file_metadata.url
#     users_db[current_user.username] = user
    
#     return file_metadata

# @app.post("/upload/menu-image/{restaurant_id}", response_model=FileMetadata, tags=["Files"])
# async def upload_menu_image(
#     restaurant_id: str,
#     file: UploadFile = File(...),
#     description: Optional[str] = Form(None),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Upload a menu image or PDF for a restaurant"""
#     if restaurant_id not in restaurants_db:
#         raise HTTPException(status_code=404, detail="Restaurant not found")
    
#     # Check if user is admin or the creator of the restaurant
#     if current_user.role != UserRole.ADMIN and restaurants_db[restaurant_id].created_by != current_user.id:
#         raise HTTPException(status_code=403, detail="Not enough permissions")
    
#     file_metadata = await save_upload_file(
#         upload_file=file,
#         category="menu_images",
#         user_id=current_user.id,
#         related_id=restaurant_id,
#         description=description
#     )
    
#     return file_metadata

@app.post("/upload/file", response_model=FileMetadata, tags=["Files"])
async def upload_generic_file(
    file: UploadFile = File(...),
    category: str = Form("other"),
    related_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """Upload a generic file"""
    # Validate category
    if category not in ["food_images", "restaurant_images", "user_images", "menu_images", "other"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category"
        )
    
    file_metadata = await save_upload_file(
        upload_file=file,
        category=category,
        # user_id=current_user.id,
        related_id=related_id,
        description=description
    )
    
    return file_metadata

@app.get("/files", response_model=List[FileMetadata], tags=["Files"])
async def get_files(
    category: Optional[str] = None,
    related_id: Optional[str] = None
    # current_user: User = Depends(get_current_active_user)
):
    """Get files with optional filtering"""
    if related_id:
        return get_files_by_related_id(related_id)
    elif category:
        return get_files_by_category(category)
    # else:
    #     # If no filters, return user's files or all files for admin
    #     if current_user.role == UserRole.ADMIN:
    #         return list(files_db.values()) # type: ignore
    #     else:
    #         return get_files_by_user(current_user.id)

@app.get("/files/{file_id}", response_model=FileMetadata, tags=["Files"])
async def get_file(
    file_id: str,
    # current_user: User = Depends(get_current_active_user)
):
    """Get metadata for a specific file"""
    return get_file_metadata(file_id)

# @app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Files"])
# async def remove_file(
#     file_id: str,
#     # current_user: User = Depends(get_current_active_user)
# ):
#     """Delete a file"""
#     is_admin = current_user.role == UserRole.ADMIN
#     await delete_file(file_id, current_user.id, is_admin)
#     return None

# Add these new endpoints at the end of the file, before the `if __name__ == "__main__"` block:

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

