using System.Text;
using System.Text.Json;
using BackendApi.Models;
using Microsoft.AspNetCore.Mvc;

namespace BackendApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class ChatController : ControllerBase
    {
        private readonly IHttpClientFactory _httpClientFactory;

        // Inject IHttpClientFactory via constructor
        public ChatController(IHttpClientFactory httpClientFactory)
        {
            _httpClientFactory = httpClientFactory;
        }

        [HttpPost]
        public async Task<IActionResult> SendMessage([FromBody] ChatRequest request)
        {
            // 1. Validate incoming request
            if (string.IsNullOrWhiteSpace(request.Message))
            {
                return BadRequest(new { error = "Message cannot be empty" });
            }

            // 2. Prepare the JSON payload for the Python AI Service
            // Python expects: { "question": "..." }
            var pythonPayload = new { question = request.Message };
            var jsonPayload = JsonSerializer.Serialize(pythonPayload);
            var httpContent = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

            // 3. Make the HTTP POST request to the Python service
            var client = _httpClientFactory.CreateClient();
            
            // NOTE: Make sure Python is running on port 8000
            var pythonResponse = await client.PostAsync("http://localhost:8000/ask", httpContent);

            if (!pythonResponse.IsSuccessStatusCode)
            {
                // Handle errors if Python service is down or returns an error
                return StatusCode(500, new { error = "Failed to communicate with AI service" });
            }

            // 4. Parse the response from Python
            var responseString = await pythonResponse.Content.ReadAsStringAsync();
            using var jsonDocument = JsonDocument.Parse(responseString);
            
            // Extract the "answer" field from the Python JSON response
            var aiAnswer = jsonDocument.RootElement.GetProperty("answer").GetString();

            // 5. Construct the final response format for the React frontend
            var finalResponse = new ChatResponse
            {
                Id = Guid.NewGuid().ToString(),
                Role = "assistant",
                Content = aiAnswer ?? "Error: No answer received from AI."
            };

            return Ok(finalResponse);
        }
    }
}