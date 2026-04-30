using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Mvc;
using Microsoft.IdentityModel.Tokens;

namespace BackendApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class AuthController : ControllerBase
    {
        private readonly IConfiguration _config;

        public AuthController(IConfiguration config)
        {
            _config = config;
        }

        public class LoginRequest { public string Username { get; set; } = string.Empty; public string Password { get; set; } = string.Empty; }

        [HttpPost("login")]
        public IActionResult Login([FromBody] LoginRequest request)
        {
            // [DAY 14]: This is a mock login endpoint. In a real system, you'd validate against a user database.
            if (request.Username == "admin" && request.Password == "password")
            {
                var secretKey = _config["JWT_SECRET_KEY"]!;
                var securityKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secretKey));
                var credentials = new SigningCredentials(securityKey, SecurityAlgorithms.HmacSha256);

                var claims = new[]
                {
                    new Claim(JwtRegisteredClaimNames.Sub, request.Username),
                    new Claim("userId", "user_1001") // In a real system, this would be the actual user ID from the database
                };

                var token = new JwtSecurityToken(
                    issuer: _config["Jwt:Issuer"],
                    audience: _config["Jwt:Audience"],
                    claims: claims,
                    expires: DateTime.Now.AddHours(2), // Token valid for 2 hours
                    signingCredentials: credentials);

                return Ok(new { token = new JwtSecurityTokenHandler().WriteToken(token) });
            }

            return Unauthorized(new { error = "Invalid credentials" });
        }
    }
}