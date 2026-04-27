using Microsoft.AspNetCore.Mvc;

namespace BackendApi.Controllers
{
    // Sets the base route to /api/health
    [ApiController]
    [Route("api/[controller]")]
    public class HealthController : ControllerBase
    {
        // Handles GET /api/health requests
        [HttpGet]
        public IActionResult CheckHealth()
        {
            // Returns a 200 OK with a simple JSON object
            return Ok(new { status = "Healthy", timestamp = DateTime.UtcNow });
        }
    }
}