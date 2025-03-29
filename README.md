# Enhanced Food Recommendation API

A comprehensive FastAPI application that provides food and drink recommendations, restaurant listings, menu management, user preferences, ratings, and wishlist functionality.

## Features

- **Foods & Drinks Listing**: Browse both food and drink items with detailed information
- **Rating System**: Rate and review food items and restaurants
- **Language & Dark Mode**: User preferences for language and UI theme
- **Menu Management**: Detailed restaurant menus with sections and items
- **Wishlist Functionality**: Save favorite food items and restaurants
- **Restaurant Listings**: Comprehensive restaurant information including contact details and social media
- **User Authentication**: Secure login and registration with JWT tokens
- **Food Recommendations**: Get personalized recommendations based on trending items and high ratings
- **Search & Filtering**: Advanced search capabilities with multiple filtering options
- **Enhanced Review System**: 
  - Vote on reviews as helpful or unhelpful
  - Report inappropriate reviews
  - Restaurant owner responses to reviews
  - Review analytics with rating distribution and keyword analysis
  - Advanced filtering and pagination for reviews
- **File Upload System**: Upload and manage images and files for food items, restaurants, menus, and user profiles

## Installation

### Using Docker Compose (Recommended)

1. Clone this repository
2. Create a `.env` file from the example:
   \`\`\`
   cp .env.example .env
   \`\`\`
3. Start the services:
   \`\`\`
   docker-compose up -d
   \`\`\`
4. The API will be available at http://localhost:8000
5. PgAdmin will be available at http://localhost:5050 (login with admin@example.com / admin)

### Using Python

1. Clone this repository
2. Install dependencies:
   \`\`\`
   pip install -r requirements.txt
   \`\`\`
3. Run the application:
   \`\`\`
   uvicorn main:app --reload
   \`\`\`

### Using Docker

1. Build the Docker image:
   \`\`\`
   docker build -t food-recommendation-api .
   \`\`\`
2. Run the container:
   \`\`\`
   docker run -p 8000:8000 food-recommendation-api
   \`\`\`

## API Documentation

Once the application is running, you can access the Swagger UI documentation at:

### Enhanced Review System
- `GET /ratings` - Get ratings with advanced filtering and pagination
- `POST /ratings/{rating_id}/votes` - Vote on a rating as helpful or unhelpful
- `DELETE /ratings/{rating_id}/votes` - Remove your vote from a rating
- `GET /ratings/{rating_id}/votes` - Get the vote counts for a rating
- `POST /ratings/{rating_id}/report` - Report a rating for inappropriate content
- `GET /admin/reports` - Get all rating reports (admin only)
- `PUT /admin/reports/{report_id}` - Update the status of a report (admin only)
- `POST /ratings/{rating_id}/response` - Respond to a rating (restaurant owners or admins)
- `PUT /ratings/{rating_id}/response` - Update a response to a rating
- `GET /ratings/{rating_id}/response` - Get the response to a rating
- `DELETE /ratings/{rating_id}/response` - Delete a response to a rating
- `GET /food-items/{food_id}/review-analytics` - Get analytics for reviews of a specific food item
- `GET /restaurants/{restaurant_id}/review-analytics` - Get analytics for reviews of a specific restaurant

### File Uploads
- `POST /upload/food-image/{food_id}` - Upload an image for a food item
- `POST /upload/restaurant-image/{restaurant_id}` - Upload an image for a restaurant
- `POST /upload/user-image` - Upload a profile image for the current user
- `POST /upload/menu-image/{restaurant_id}` - Upload a menu image or PDF for a restaurant
- `POST /upload/file` - Upload a generic file
- `GET /files` - Get files with optional filtering
- `GET /files/{file_id}` - Get metadata for a specific file
- `DELETE /files/{file_id}` - Delete a file

### Get Filtered Reviews

\`\`\`
GET /ratings?restaurant_id=1&min_rating=4&sort_by=most_helpful&limit=10
\`\`\`

### Vote on a Review

\`\`\`
POST /ratings/1/votes
{
  "vote_type": "helpful"
}
\`\`\`

### Get Review Analytics

\`\`\`
GET /food-items/1/review-analytics
\`\`\`

Response:
\`\`\`json
{
  "total_reviews": 42,
  "average_rating": 4.7,
  "rating_distribution": {
    "1": 0,
    "2": 1,
    "3": 2,
    "4": 10,
    "5": 29
  },
  "recent_trend": 0.2,
  "most_mentioned_keywords": [
    {"word": "delicious", "count": 15},
    {"word": "authentic", "count": 8},
    {"word": "flavor", "count": 7}
  ]
}
\`\`\`

### Respond to a Review (Restaurant Owner)

\`\`\`
POST /ratings/1/response
{
  "response_text": "Thank you for your feedback! We're glad you enjoyed our carbonara and hope to see you again soon."
}
\`\`\`

### Upload a Food Image

\`\`\`
POST /upload/food-image/1
Content-Type: multipart/form-data

file: [binary data]
description: "Delicious carbonara pasta"
\`\`\`

### Get All Files for a Restaurant

\`\`\`
GET /files?related_id=1
\`\`\`

### Delete a File

\`\`\`
DELETE /files/file_id
\`\`\`

