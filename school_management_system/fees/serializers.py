from rest_framework import serializers
from .models import FeeBalance, FeePayment, FeeStructure


class FeeStructureSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True)

    class Meta:
        model = FeeStructure
        fields = ["id", "grade", "grade_name", "term", "term_name", "amount", "description"]
        read_only_fields = ["id"]


class FeePaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FeePayment
        fields = [
            "id", "enrollment", "student_name",
            "fee_structure",
            "amount_paid", "payment_date",
            "payment_method", "receipt_number",
            "notes", "recorded_by", "recorded_by_name",
        ]
        read_only_fields = ["id", "receipt_number", "payment_date"]

    def get_student_name(self, obj: FeePayment) -> str:
        return obj.enrollment.student.get_full_name()

    def get_recorded_by_name(self, obj: FeePayment) -> str | None:
        if obj.recorded_by:
            return obj.recorded_by.get_full_name() or obj.recorded_by.username
        return None

    def create(self, validated_data: dict) -> FeePayment:
        validated_data["recorded_by"] = self.context["request"].user
        return super().create(validated_data)


class FeeBalanceSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    term_name = serializers.CharField(source="term.name", read_only=True)
    payment_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = FeeBalance
        fields = [
            "id", "enrollment", "student_name",
            "term", "term_name",
            "total_fee", "amount_paid", "balance",
            "is_paid", "payment_percentage", "last_updated",
        ]
        read_only_fields = ["id", "amount_paid", "balance", "is_paid", "last_updated"]

    def get_student_name(self, obj: FeeBalance) -> str:
        return obj.enrollment.student.get_full_name()
