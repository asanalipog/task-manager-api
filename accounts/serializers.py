
from rest_framework import serializers
from django.contrib.auth import get_user_model


User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        extra_kwargs = {
            "password": {"write_only": True, 'style': {'input_type': 'password'}}
        }
        
    def create(self, validated_data):
        # Remove password from validated_data to handle it separately
        password = validated_data.pop('password', None)
        
        # Create user instance without the password first
        user = self.Meta.model(**validated_data)
        
        if password is not None:
            # Hash the plain text password properly
            user.set_password(password)
            
        user.save()
        return user
