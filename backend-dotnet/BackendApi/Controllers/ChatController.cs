using BackendApi.Models;
using Microsoft.AspNetCore.Mvc;

namespace BackendApi.Controllers
{
    // Sets the base route to /api/chat
    [ApiController]
    [Route("api/[controller]")]
    public class ChatController : ControllerBase
    {
        // Handles POST /api/chat requests
        [HttpPost]
        public IActionResult SendMessage([FromBody] ChatRequest request)
        {
            // 1. Validate the incoming request
            if (string.IsNullOrWhiteSpace(request.Message))
            {
                return BadRequest(new { error = "Message cannot be empty" });
            }

            // 2. Create a mock AI response
            var mockResponse = new ChatResponse
            {
                Id = Guid.NewGuid().ToString(), // Generate a unique ID
                Role = "assistant",
                Content = $"[Mocked .NET API] I received your message: '{request.Message}'. Real AI logic will be added later."
            };

            // 3. Return the response with a 200 OK status
            return Ok(mockResponse);
        }
    }
}