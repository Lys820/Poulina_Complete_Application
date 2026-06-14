namespace PouleLabApp.API.Models
{
    /// <summary>
    /// Poultry farming center affiliated with a Poulina subsidiary.
    /// Seeded at startup via DataSeeder.
    /// </summary>
    public class FarmCenter
    {
        public int      Id             { get; set; }
        public string   Name           { get; set; } = string.Empty;
        public string   Governorate    { get; set; } = string.Empty;
        public string   Address        { get; set; } = string.Empty;
        public int      Capacity       { get; set; }  // number of heads
        public string   FarmingType    { get; set; } = string.Empty; // "Broiler", "Layer", "Turkey", "Mixed"
        public bool     IsActive       { get; set; } = true;
        public DateTime CreatedAt      { get; set; } = DateTime.UtcNow;
    }
}