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
        // NEW: Inject ILogger for structured logging
        private readonly ILogger<ChatController> _logger;

        public ChatController(IHttpClientFactory httpClientFactory, ILogger<ChatController> logger)
        {
            _httpClientFactory = httpClientFactory;
            _logger = logger;
        }

        [HttpPost]
        public async Task<IActionResult> SendMessage([FromBody] ChatRequest request)
        {
            // Log the incoming request
            _logger.LogInformation("Received message request. Content length: {Length}", request.Message?.Length ?? 0);

            if (string.IsNullOrWhiteSpace(request.Message))
            {
                _logger.LogWarning("Validation failed: Received an empty message.");
                return BadRequest(new { error = "Message cannot be empty" });
            }

            try
            {
                var pythonPayload = new { question = request.Message };
                var jsonPayload = JsonSerializer.Serialize(pythonPayload);
                var httpContent = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                var client = _httpClientFactory.CreateClient();
                
                _logger.LogInformation("Sending request to Python AI Service...");
                
                // NOTE: If Python service is down, this might throw an HttpRequestException
                var pythonResponse = await client.PostAsync("http://localhost:8000/ask", httpContent);

                // Handle non-200 HTTP responses from Python
                if (!pythonResponse.IsSuccessStatusCode)
                {
                    _logger.LogError("Python AI Service returned an error. Status Code: {StatusCode}", pythonResponse.StatusCode);
                    return StatusCode(500, new { error = "Failed to communicate with AI service." });
                }

                var responseString = await pythonResponse.Content.ReadAsStringAsync();
                
                // Safely parse JSON
                using var jsonDocument = JsonDocument.Parse(responseString);
                var aiAnswer = jsonDocument.RootElement.GetProperty("answer").GetString();

                _logger.LogInformation("Successfully received response from Python AI Service.");

                var finalResponse = new ChatResponse
                {
                    Id = Guid.NewGuid().ToString(),
                    Role = "assistant",
                    Content = aiAnswer ?? "Error: No answer received from AI."
                };

                return Ok(finalResponse);
            }
            // Catch specific network exceptions
            catch (HttpRequestException httpEx)
            {
                _logger.LogError(httpEx, "Network error occurred while connecting to Python AI Service.");
                return StatusCode(503, new { error = "AI Service is currently unavailable." });
            }
            // Catch any other unexpected exceptions (e.g., JSON parsing errors)
            catch (Exception ex)
            {
                _logger.LogCritical(ex, "An unexpected error occurred in the ChatController.");
                return StatusCode(500, new { error = "An internal server error occurred." });
            }
        }
    }
}