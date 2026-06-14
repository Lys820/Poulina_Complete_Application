namespace PouleLabApp.API.DTOs.User
{
    public class UpdateProfileDto
    {
        public string FirstName      { get; set; } = string.Empty;
        public string LastName       { get; set; } = string.Empty;
        public string? PhoneNumber   { get; set; }
        public string? FilialeName   { get; set; }
        public string? CurrentPassword { get; set; }
        public string? NewPassword   { get; set; }
    }
}