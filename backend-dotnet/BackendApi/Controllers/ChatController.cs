using System.Text;
using System.Text.Json;
using BackendApi.Models;
using Microsoft.AspNetCore.Mvc;
using Npgsql;
using Microsoft.Extensions.Configuration;
using Microsoft.AspNetCore.Authorization;

namespace BackendApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize]
    public class ChatController : ControllerBase
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly ILogger<ChatController> _logger;
        private readonly string _connectionString;
        private readonly string _pythonServiceUrl;

        public ChatController(IHttpClientFactory httpClientFactory, ILogger<ChatController> logger, IConfiguration configuration)
        {
            _httpClientFactory = httpClientFactory;
            _logger = logger;
            _connectionString = configuration["SUPABASE_DB_CONNECTION"] 
                                ?? throw new InvalidOperationException("DB Connection string not found in .env");
            _pythonServiceUrl = configuration["PYTHON_SERVICE_URL"] 
                                ?? "http://127.0.0.1:8000";
        }

        [HttpPost]
        public async Task<IActionResult> SendMessage([FromBody] ChatRequest request)
        {
            if (string.IsNullOrWhiteSpace(request.Message)) return BadRequest(new { error = "Message empty" });

            // Hardcode a session ID for now (Day 14 will attach it to users)
            string sessionId = "session_123";

            try
            {
                // [DAY 13]: Save User Message to DB
                await SaveMessageToDb(sessionId, "user", request.Message);

                // Call Python AI Service
                var pythonPayload = new { question = request.Message };
                var jsonPayload = JsonSerializer.Serialize(pythonPayload);
                var httpContent = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                var client = _httpClientFactory.CreateClient();
                var pythonResponse = await client.PostAsync($"{_pythonServiceUrl}/ask", httpContent);
                pythonResponse.EnsureSuccessStatusCode();

                var responseString = await pythonResponse.Content.ReadAsStringAsync();
                using var jsonDocument = JsonDocument.Parse(responseString);
                var aiAnswer = jsonDocument.RootElement.GetProperty("answer").GetString() ?? "Error";

                // [DAY 13]: Save AI Assistant Message to DB
                await SaveMessageToDb(sessionId, "assistant", aiAnswer);

                return Ok(new ChatResponse { Id = Guid.NewGuid().ToString(), Role = "assistant", Content = aiAnswer });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Chat processing failed.");
                return StatusCode(500, new { error = "Internal server error." });
            }
        }

        // Helper method to execute SQL insert
        private async Task SaveMessageToDb(string sessionId, string role, string content)
        {
            await using var conn = new NpgsqlConnection(_connectionString);
            await conn.OpenAsync();
            await using var cmd = new NpgsqlCommand("INSERT INTO chat_messages (session_id, role, content) VALUES (@s, @r, @c)", conn);
            cmd.Parameters.AddWithValue("s", sessionId);
            cmd.Parameters.AddWithValue("r", role);
            cmd.Parameters.AddWithValue("c", content);
            await cmd.ExecuteNonQueryAsync();
        }
    }
}