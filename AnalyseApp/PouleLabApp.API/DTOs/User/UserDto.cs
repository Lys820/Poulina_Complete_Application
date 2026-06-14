public class UserDto
{
    public string Id          { get; set; } = string.Empty;
    public string FirstName   { get; set; } = string.Empty;
    public string LastName    { get; set; } = string.Empty;
    public string Email       { get; set; } = string.Empty;
    public string? PhoneNumber { get; set; }
    public int?    LaboratoryId   { get; set; }
    public string? LaboratoryName { get; set; }
    public string? FilialeName { get; set; }
    public bool   IsActive    { get; set; }
    public bool IsApproved { get; set; }
    public string Role        { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
}