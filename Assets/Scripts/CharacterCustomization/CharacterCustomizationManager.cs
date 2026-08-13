using System;
using UnityEngine;

namespace CharacterCustomization
{
    /// <summary>
    /// Facade tying together morphology, appearance and equipment so callers (UI,
    /// save/load, network sync) have a single entry point instead of touching each
    /// sub-controller directly.
    /// </summary>
    public class CharacterCustomizationManager : MonoBehaviour
    {
        [SerializeField] private MorphController morphController;
        [SerializeField] private AppearanceController appearanceController;
        [SerializeField] private EquipmentManager equipmentManager;
        [SerializeField] private ClothingItem[] clothingCatalog;

        public MorphController Morphs => morphController;
        public AppearanceController Appearance => appearanceController;
        public EquipmentManager Equipment => equipmentManager;

        public void ApplyDefaults()
        {
            morphController.ApplyDefaults();
            appearanceController.SetSkinColor(Color.white);
        }

        public ClothingItem FindClothing(string id)
        {
            return Array.Find(clothingCatalog, c => c.id == id);
        }

        public CharacterData Capture()
        {
            var data = new CharacterData
            {
                skinColor = appearanceController.CurrentSkinColor,
                hairId = appearanceController.CurrentHairId,
                hairColor = appearanceController.CurrentHairColor
            };

            foreach (var slider in morphController.Profile.sliders)
            {
                data.morphs.Add(new MorphValue
                {
                    sliderId = slider.id,
                    weight = morphController.GetValue(slider.id)
                });
            }

            foreach (EquipmentSlot slot in Enum.GetValues(typeof(EquipmentSlot)))
            {
                var item = equipmentManager.GetEquipped(slot);
                if (item != null)
                {
                    data.equippedItems.Add(new EquippedItem
                    {
                        slot = slot,
                        itemId = item.id,
                        tint = item.defaultTint
                    });
                }
            }

            return data;
        }

        public void Apply(CharacterData data)
        {
            foreach (var morph in data.morphs)
            {
                morphController.SetValue(morph.sliderId, morph.weight);
            }

            appearanceController.SetSkinColor(data.skinColor);
            appearanceController.SetHair(data.hairId, data.hairColor);

            foreach (var equipped in data.equippedItems)
            {
                var item = FindClothing(equipped.itemId);
                if (item != null)
                {
                    equipmentManager.Equip(item, equipped.tint);
                }
            }
        }
    }
}
