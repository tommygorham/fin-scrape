import requests

def verify_quiver_api_connection(
    base_url: str = "https://api.quiverquant.com",
    token: str = "c2e4fb49d96e06519b4812450ac9badf726150ef"
) -> dict:
    """
    Verify connection to the Quiver API.
    
    Args:
        base_url: Base URL for the Quiver API
        token: Authorization bearer token
        
    Returns:
        dict: Connection status with 'success' boolean and 'message' string
    """
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        # Use the premium auth endpoint to verify connection
        response = requests.get(
            f"{base_url}/beta/auth/premium",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "message": "API connection verified successfully",
                "status_code": response.status_code,
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "message": f"API returned status code {response.status_code}",
                "status_code": response.status_code,
                "error": response.text
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "Connection timed out",
            "error": "Request exceeded 10 second timeout"
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "message": "Failed to connect to API",
            "error": "Could not establish connection"
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Unexpected error occurred",
            "error": str(e)
        }


# Usage example
if __name__ == "__main__":
    result = verify_quiver_api_connection()
    
    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"  Status: {result.get('data', {}).get('status', 'N/A')}")
    else:
        print(f"✗ {result['message']}")
        print(f"  Error: {result.get('error', 'Unknown')}")
