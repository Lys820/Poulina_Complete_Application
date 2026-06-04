namespace PouleLabApp.API.DTOs.Request
{
    public class DeadlineDto
    {
        public int      Id                 { get; set; }
        public int      SampleId           { get; set; }
        public string   SampleType         { get; set; } = string.Empty;
        public bool     IsPerishable       { get; set; }
        public DateTime? ExpiryDate        { get; set; }
        public string   UrgencyLevel       { get; set; } = "Normal";
        public string   UrgencyDescription { get; set; } = string.Empty;
    }

    public class SetDeadlineDto
    {
        public int      SampleId           { get; set; }
        public bool     IsPerishable       { get; set; }
        public DateTime? ExpiryDate        { get; set; }
        public string   UrgencyLevel       { get; set; } = "Normal";
        public string   UrgencyDescription { get; set; } = string.Empty;
    }
}