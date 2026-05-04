from django.db import models

class AttendanceRecord(models.Model):
    enrollment = models.ForeignKey('students.Enrollment', on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=(('present','Present'), ('absent','Absent'), ('late','Late')))
    remark = models.TextField(blank=True)

    class Meta:
        unique_together = ('enrollment', 'date')
