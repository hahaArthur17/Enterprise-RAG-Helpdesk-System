using Microsoft.AspNetCore.Mvc;

namespace BackendApi.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ChatController : ControllerBase
{
    [HttpPost]
    public IActionResult Post([FromBody] string message)
    {
        return Ok(new { reply = "Hello from .NET API" });
    }
}
