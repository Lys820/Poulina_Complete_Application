using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Data
{
    public class ApplicationDbContext : IdentityDbContext<ApplicationUser>
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options) { }

        public DbSet<Laboratory>      Laboratories   => Set<Laboratory>();
        public DbSet<AnalysisRequest> AnalysisRequests => Set<AnalysisRequest>();
        public DbSet<Sample>          Samples        => Set<Sample>();
        public DbSet<AnalysisResult>  AnalysisResults => Set<AnalysisResult>();
        public DbSet<Deadline>        Deadlines      => Set<Deadline>();
        public DbSet<AuditLog>        AuditLogs      => Set<AuditLog>();
        public DbSet<Notification>    Notifications  => Set<Notification>();
        // ← AnalysisTypes supprimé

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);

            builder.Entity<AnalysisRequest>()
                .HasOne(r => r.Client)
                .WithMany(u => u.SubmittedRequests)
                .HasForeignKey(r => r.ClientId)
                .OnDelete(DeleteBehavior.Restrict);

            builder.Entity<AnalysisRequest>()
                .HasOne(r => r.AssignedTo)
                .WithMany(u => u.AssignedRequests)
                .HasForeignKey(r => r.AssignedToId)
                .OnDelete(DeleteBehavior.Restrict);

            builder.Entity<AnalysisResult>()
                .HasOne(r => r.RecordedBy)
                .WithMany()
                .HasForeignKey(r => r.RecordedById)
                .OnDelete(DeleteBehavior.Restrict);

            builder.Entity<AuditLog>()
                .HasOne(a => a.PerformedBy)
                .WithMany()
                .HasForeignKey(a => a.PerformedById)
                .OnDelete(DeleteBehavior.Restrict);

            builder.Entity<AnalysisRequest>()
                .Property(r => r.Status)
                .HasConversion<string>();
            
            builder.Entity<Deadline>()
                .HasOne(d => d.Sample)
                .WithMany(s => s.Deadlines)
                .HasForeignKey(d => d.SampleId)
                .OnDelete(DeleteBehavior.Restrict);

            // Relation User → Laboratory (nullable, un user appartient à un labo ou pas)
            builder.Entity<ApplicationUser>()
            .HasOne(u => u.Laboratory)
            .WithMany()
            .HasForeignKey(u => u.LaboratoryId)
            .OnDelete(DeleteBehavior.SetNull); // ← si le labo est supprimé, LaboratoryId = null                
        }
    }
}